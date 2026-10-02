#!/usr/bin/env python3
"""Independent validator for the BAT-710 national Division I population 2016-2025 (Cycle #38 Attempt #1).

Every checked fact is reconstructed from raw lake bytes and the contract.  The validator uses the Python
standard library only, imports no repository module and never reads producer source (AGENTS rule 9).  Lake
files are opened read-only; the only write is the create-only ``--report`` file.

Stages (exit 0 = every check PASS, 1 = any check FAIL, 2 = REFUSED):

  inputs          L02 INPUT_BINDING: binding rule, capture rehash, CFBD routes, bound file hashes.
  program-season  L07 VALIDATE_M1: raw page decode, expected keys, dispositions, decoding proof, totals.
  contest         L09 VALIDATE_M2: contest reconstruction, FCS-FCS, orientations, reconciliation, cardinality.
  subsets         FBS_ESTIMAND_SUBSET / FCS_SUBSET re-filtered from the parent contest rows.
"""

import argparse
import collections
import datetime
import gzip
import hashlib
import html
import json
import pathlib
import re
import sys
import time

POPULATION = "national_di_population_2016_2025"
REPORT_LABEL = "Cycle #38 — Attempt #1 — IN_PROGRESS_LOCAL_WORK_REMAINS"
CYCLE_NUMBER = 38
ATTEMPT_NUMBER = 1
STAGES = ("inputs", "program-season", "contest", "subsets")
DISCOVERY_PARTS = ("manifests", "acquisition", "BAT-554-NCAA-OFFICIAL-BOUNDED-V1", "discovery")
DISCOVERY_FILE = "ncaa_team_graph_discovery_manifest.json"
SRC015_PARTS = ("raw", "SRC-015", "ncaa_team_season_discovery")
SRC002_GAMES_PARTS = ("raw", "SRC-002", "games")
CYCLE30_GAMES_PARTS = ("ops", "cycle30_work", "raw", "games")
ADJACENT_SEASON = 2015
BINDING_SEASONS = tuple(range(2015, 2026))
HEAD_LIMIT = 50
MANIFEST_KEYS = ("identity", "identity_document", "issued_at_utc", "label", "row_counts")
IDENTITY_DOCUMENT_KEYS = ("schema", "population", "stage", "contract_sha256", "producer", "inputs", "upstream", "outputs")

# Expectations stated by the validator specification (VALIDATOR_SPEC_C38A01.md); deviations are FAIL.
SPEC_EXPECTED_FAILURES = {2016: 4, 2017: 4}
SPEC_EXPECTED_UNREFERENCED_SRC015 = 64
SPEC_EXPECTED_CODE_TALLIES = {
    2016: {"11": 127, "12": 124, "2": 171, "3": 234, "none": 3},
    2019: {"11": 130, "12": 126, "2": 167, "3": 237, "none": 0},
}
SPEC_EXPECTED_DECODING_PROOF = {"total": 562, "FBS": 380, "FCS": 163, "D-II": 19}

# Official team-history division labels and the page code each one agrees with (D-III with 3 is agreement).
HISTORY_LABEL_TO_CODE = {"FBS": "11", "FCS": "12", "D-II": "2", "D-III": "3"}
DIVISION_I_HISTORY_LABELS = ("FBS", "FCS")
PROOF_LABELS = ("FBS", "FCS", "D-II")

RE_TAG = re.compile(r"<[^>]+>")
RE_HISTORY_LINK = re.compile(r'href="/teams/history/MFB/(\d+)"')
RE_YEAR_SELECT = re.compile(r'<select\b[^>]*\bid="year_list"[^>]*>(.*?)</select>', re.S)
RE_OPTION = re.compile(r"<option\b([^>]*)>(.*?)</option>", re.S)
RE_VALUE_ATTR = re.compile(r'\bvalue="([^"]*)"')
RE_SELECTED_ATTR = re.compile(r"\bselected\b")
RE_RANKING_HREF = re.compile(r'href="(/rankings/[^"]*)"')
RE_DIVISION_PARAM = re.compile(r"[?&]division=([^&#]*)")
RE_CODE_FORM = re.compile(r"^(0|[1-9][0-9]*)(\.0)?$")
RE_CARD_HEADER = re.compile(r'<div class="card-header">(.*?)</div>', re.S)
RE_HEADER_RECORD = re.compile(r"^(.*?)\s*\((\d+)-(\d+)(?:-(\d+))?\)\s*(?:\*\s*(.*))?$", re.S)
RE_SCHEDULE_HEADER = re.compile(r'<div class="card-header">\s*Schedule/Results\s*</div>')
RE_SCHEDULE_ROW = re.compile(r'<tr class="underline_rows">(.*?)</tr>', re.S)
RE_TD = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S)
RE_BR = re.compile(r"<br\s*/?>", re.I)
RE_TEAM_LINK = re.compile(r'<a\b[^>]*\bhref="/teams/(\d+)"[^>]*>(.*?)</a>', re.S)
RE_IMG = re.compile(r"<img\b[^>]*>", re.S)
RE_ALT_ATTR = re.compile(r'\balt="([^"]*)"')
RE_LOGO_ORG = re.compile(r"/sm//(\d+)\.gif")
RE_CONTEST_LINK = re.compile(r'<a\b[^>]*\bhref="/contests/(\d+)/box_score"[^>]*>(.*?)</a>(.*)$', re.S)
RE_SCORE = re.compile(r"^([WLT])\s+(\d+)\s*-\s*(\d+)(?:\s*\(\s*(-?\d+)\s*OT\s*\))?$")
RE_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})(\s+\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?)?$")
RE_SITE_EVENT = re.compile(r"^(.*?)\s*\(([^()]*)\)\s*$")
RE_HISTORY_ORG_INPUT = re.compile(r'<input\b[^>]*\bid="org_id_search"[^>]*>')
RE_HISTORY_TABLE = re.compile(r'<table\b[^>]*\bid="team_history_data_table"[^>]*>(.*?)</table>', re.S)
RE_TR = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
RE_HISTORY_YEAR = re.compile(r'<a\b[^>]*\bhref="/teams/(\d+)"[^>]*>\s*(\d{4})-(\d{2})\s*</a>')
RE_IMPORT_LINE = re.compile(r"(?m)^import ([A-Za-z_][A-Za-z0-9_]*)\s*$")


class Refusal(Exception):
    """A refusal: missing/malformed input or a contract/manifest identity mismatch (exit 2)."""

    def __init__(self, code, detail):
        super().__init__(code)
        self.code = code
        self.detail = detail


class Check:
    def __init__(self, name):
        self.name = name
        self.counts = {}
        self.head = []
        self.disagreement_count = 0

    def disagree(self, item):
        self.disagreement_count += 1
        if len(self.head) < HEAD_LIMIT:
            self.head.append(item)

    def to_json(self):
        return {
            "result": "PASS" if self.disagreement_count == 0 else "FAIL",
            "counts": self.counts,
            "disagreements_head": self.head,
            "disagreement_count": self.disagreement_count,
        }


class Context:
    def __init__(self, args):
        self.args = args
        self.stage = args.stage
        self.contract_path = pathlib.Path(args.contract)
        self.data_root = pathlib.Path(args.data_root)
        if args.repo_root:
            self.repo_root = pathlib.Path(args.repo_root)
        else:
            self.repo_root = pathlib.Path(__file__).resolve().parents[1]
        self.manifest_path = pathlib.Path(args.manifest) if args.manifest else None
        self.contract = None
        self.contract_sha256 = None
        self.manifest_identity = None
        self.checks = collections.OrderedDict()

    def check(self, name):
        if name not in self.checks:
            self.checks[name] = Check(name)
        return self.checks[name]


# ----------------------------------------------------------------------------------------------- helpers


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1 << 20)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(document):
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(text.encode("utf-8"))


def season_label(season):
    return "%d-%02d" % (season, (season + 1) % 100)


def parse_instant(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        instant = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if instant.tzinfo is None or instant.utcoffset() is None:
        return None
    return instant


def text_of(fragment):
    return " ".join(html.unescape(RE_TAG.sub(" ", fragment)).split())


def name_key(name):
    return " ".join((name or "").lower().split())


def counter_dict(counter):
    return {str(key): counter[key] for key in sorted(counter, key=str)}


def delivery_seasons(ctx):
    seasons = ctx.contract.get("delivery_seasons")
    if not isinstance(seasons, list) or not seasons or not all(isinstance(s, int) for s in seasons):
        raise Refusal("CONTRACT_MALFORMED", "delivery_seasons is not a non-empty integer list")
    return sorted(seasons)


def contract_section(ctx, *path):
    node = ctx.contract
    for key in path:
        if not isinstance(node, dict) or key not in node:
            raise Refusal("CONTRACT_MALFORMED", "contract is missing %s" % ".".join(path))
        node = node[key]
    return node


def data_path(ctx, relative):
    return ctx.data_root.joinpath(*[part for part in relative.replace("\\", "/").split("/") if part])


def bound_input_path(ctx, relative):
    clean = relative.replace("\\", "/")
    if clean.startswith("artifacts/"):
        return ctx.repo_root.joinpath(*[part for part in clean.split("/") if part])
    return data_path(ctx, clean)


def read_jsonl_gz_bytes(data, label):
    try:
        text = gzip.decompress(data).decode("utf-8")
    except (OSError, EOFError, UnicodeDecodeError) as exc:
        raise Refusal("OUTPUT_MALFORMED", "%s is not gzip UTF-8 (%s)" % (label, exc))
    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        raise Refusal("OUTPUT_MALFORMED", "%s is empty" % label)
    try:
        first = json.loads(lines[0])
        rows = [json.loads(line) for line in lines[1:]]
    except json.JSONDecodeError as exc:
        raise Refusal("OUTPUT_MALFORMED", "%s has a malformed JSON line (%s)" % (label, exc))
    if not isinstance(first, dict) or set(first) != {"_header"} or not isinstance(first["_header"], dict):
        raise Refusal("OUTPUT_MALFORMED", "%s first line is not a {_header} object" % label)
    for row in rows:
        if not isinstance(row, dict):
            raise Refusal("OUTPUT_MALFORMED", "%s contains a non-object row" % label)
    return first["_header"], rows


def own_imports():
    try:
        source = pathlib.Path(__file__).read_text(encoding="utf-8")
    except OSError:
        return []
    return sorted(set(RE_IMPORT_LINE.findall(source)))


# ------------------------------------------------------------------------------------------ raw parsers


def decode_division(raw_codes):
    """Return (decode_state, canonical code or None) from the page's own ranking-link division values."""
    canonical = set()
    malformed = False
    for value in raw_codes:
        match = RE_CODE_FORM.match(value)
        if not match:
            malformed = True
            continue
        canonical.add(match.group(1))
    if malformed:
        return "MALFORMED_CODE", None
    if not canonical:
        return "NO_CODE", None
    if len(canonical) > 1:
        return "MULTIPLE_CODES", None
    code = next(iter(canonical))
    if code not in ("11", "12", "2", "3"):
        return "UNKNOWN_CODE", code
    return "DECODED", code


def parse_opponent_cell(cell):
    parts = RE_BR.split(cell, maxsplit=1)
    first = parts[0].strip()
    second = parts[1] if len(parts) > 1 else ""
    away = first.startswith("@")
    if away:
        first = first[1:].strip()
    row = {"away": away, "opp_ts": None, "opp_name": None, "opp_logo_org": None,
           "neutral_site": None, "event_label": None}
    link = RE_TEAM_LINK.search(first)
    if link:
        row["opp_ts"] = link.group(1)
        img = RE_IMG.search(link.group(2))
        name = None
        if img:
            alt = RE_ALT_ATTR.search(img.group(0))
            if alt:
                name = " ".join(html.unescape(alt.group(1)).split())
            logo = RE_LOGO_ORG.search(img.group(0))
            if logo:
                row["opp_logo_org"] = logo.group(1)
        row["opp_name"] = name if name else text_of(link.group(2))
    else:
        row["opp_name"] = text_of(first)
    second_text = text_of(second)
    if second_text.startswith("@"):
        site = second_text[1:].strip()
        event = RE_SITE_EVENT.match(site)
        if event:
            site, row["event_label"] = event.group(1).strip(), event.group(2).strip()
        row["neutral_site"] = site if site else "@"
    elif second_text:
        row["event_label"] = second_text
    return row


def parse_result_cell(cell):
    row = {"contest_id": None, "result_text": None, "status": None, "letter": None, "p": None, "q": None,
           "ot": None, "exempt": False, "flags": []}
    link = RE_CONTEST_LINK.search(cell)
    if link:
        row["contest_id"] = link.group(1)
        text = text_of(link.group(2))
        row["exempt"] = "*" in text_of(link.group(3))
    else:
        text = text_of(cell)
    row["result_text"] = text
    score = RE_SCORE.match(text)
    lowered = text.lower()
    if score:
        letter, p, q = score.group(1), int(score.group(2)), int(score.group(3))
        row.update(status="COMPLETED", letter=letter, p=p, q=q)
        if score.group(4) is not None:
            row["ot"] = int(score.group(4))
            if row["ot"] < 0:
                row["flags"].append("NEGATIVE_OVERTIME_MARKER")
        if (letter == "W" and not p > q) or (letter == "L" and not p < q) or (letter == "T" and p != q):
            row["flags"].append("RESULT_LETTER_CONTRADICTS_SCORE")
    elif lowered == "canceled" or lowered == "cancelled":
        row["status"] = "CANCELED"
    elif lowered == "ppd":
        row["status"] = "UNSCORED"
    elif "no contest" in lowered:
        row["status"] = "NO_CONTEST"
    elif "forfeit" in lowered:
        row["status"] = "FORFEIT"
    else:
        row["status"] = "UNPARSED"
        row["flags"].append("UNPARSED_RESULT")
    if row["exempt"]:
        row["flags"].append("EXEMPTED_NOT_COUNTED")
    return row


def parse_team_season_page(text):
    page = {}
    orgs = sorted(set(RE_HISTORY_LINK.findall(text)))
    page["org_ids"] = orgs
    page["org_id"] = orgs[0] if len(orgs) == 1 else None
    options = {}
    selected = []
    duplicate_labels = 0
    select = RE_YEAR_SELECT.search(text)
    if select:
        for option in RE_OPTION.finditer(select.group(1)):
            attrs = option.group(1)
            label = text_of(option.group(2))
            value_match = RE_VALUE_ATTR.search(attrs)
            value = value_match.group(1) if value_match else None
            if label in options and options[label] != value:
                duplicate_labels += 1
            options[label] = value
            if RE_SELECTED_ATTR.search(attrs):
                selected.append((label, value))
    page["season_options"] = options
    page["season_selector_present"] = select is not None
    page["duplicate_option_labels"] = duplicate_labels
    page["selected"] = selected[0] if len(selected) == 1 else None
    raw_codes = []
    for href in RE_RANKING_HREF.finditer(text):
        raw_codes.extend(RE_DIVISION_PARAM.findall(html.unescape(href.group(1))))
    page["raw_codes"] = sorted(set(raw_codes))
    page["decode_state"], page["code"] = decode_division(raw_codes)
    page["header"] = None
    for header in RE_CARD_HEADER.finditer(text):
        header_text = text_of(header.group(1))
        record = RE_HEADER_RECORD.match(header_text)
        if record:
            page["header"] = {
                "wins": int(record.group(2)),
                "losses": int(record.group(3)),
                "ties": int(record.group(4)) if record.group(4) is not None else None,
                "note": record.group(5),
                "name_text": record.group(1),
            }
            break
    rows = []
    schedule = RE_SCHEDULE_HEADER.search(text)
    page["schedule_card"] = schedule is not None
    if schedule:
        end = text.find("</table>", schedule.end())
        block = text[schedule.end(): end if end >= 0 else len(text)]
        for index, tr in enumerate(RE_SCHEDULE_ROW.finditer(block)):
            cells = RE_TD.findall(tr.group(1))
            row = {"index": index, "cells": len(cells), "date": None, "date_text": None, "flags": []}
            if len(cells) != 4:
                row["flags"].append("MALFORMED_ROW")
                row.update(away=False, opp_ts=None, opp_name=None, opp_logo_org=None, neutral_site=None,
                           event_label=None, contest_id=None, status="UNPARSED", letter=None, p=None, q=None,
                           ot=None, exempt=False, result_text=None)
                rows.append(row)
                continue
            date_text = text_of(cells[0])
            row["date_text"] = date_text
            date = RE_DATE.match(date_text)
            if date:
                try:
                    row["date"] = datetime.date(int(date.group(3)), int(date.group(1)), int(date.group(2))).isoformat()
                except ValueError:
                    row["flags"].append("MALFORMED_DATE")
                if date.group(4):
                    row["flags"].append("DATE_WITH_TIME")
            else:
                row["flags"].append("MALFORMED_DATE")
            row.update(parse_opponent_cell(cells[1]))
            result = parse_result_cell(cells[2])
            row["flags"].extend(result.pop("flags"))
            row.update(result)
            rows.append(row)
    page["rows"] = rows
    return page


def parse_team_history_page(text):
    """Return (org id, rows) or (None, None) when the page carries no team-history table."""
    table = RE_HISTORY_TABLE.search(text)
    if not table:
        return None, None
    org = None
    tag = RE_HISTORY_ORG_INPUT.search(text)
    if tag:
        value = RE_VALUE_ATTR.search(tag.group(0))
        if value:
            org = value.group(1).strip() or None
    rows = []
    for tr in RE_TR.finditer(table.group(1)):
        cells = RE_TD.findall(tr.group(1))
        if not cells:
            continue
        if len(cells) != 9:
            rows.append({"malformed": True, "cells": len(cells), "kind": "NOT_9_CELLS"})
            continue
        year = RE_HISTORY_YEAR.search(cells[0])
        if not year:
            # The career-totals footer row has nine cells and no Year link; it is not a season row.
            rows.append({"malformed": True, "cells": 9, "kind": "NO_YEAR_LINK"})
            continue
        season = int(year.group(2))
        rows.append({
            "malformed": False,
            "season": season,
            "label_ok": year.group(3) == "%02d" % ((season + 1) % 100),
            "team_season_id": year.group(1),
            "division": text_of(cells[2]),
            "conference": text_of(cells[3]),
            "wins": text_of(cells[4]),
            "losses": text_of(cells[5]),
            "ties": text_of(cells[6]),
            "pct": text_of(cells[7]),
            "notes": text_of(cells[8]),
        })
    return org, rows


# ------------------------------------------------------------------------------- discovery manifests


def discovery_entries(ctx, season):
    base = ctx.data_root.joinpath(*DISCOVERY_PARTS, str(season), "sha256")
    entries = []
    if not base.is_dir():
        return entries
    for directory in sorted(base.iterdir(), key=lambda p: p.name):
        if not directory.is_dir():
            continue
        path = directory / DISCOVERY_FILE
        entry = {"dir": directory.name, "path": path, "doc": None, "sha256": None, "problem": None}
        if not path.is_file():
            entry["problem"] = "NO_MANIFEST_FILE"
            entries.append(entry)
            continue
        raw = path.read_bytes()
        entry["sha256"] = sha256_bytes(raw)
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            entry["problem"] = "MALFORMED_JSON"
            entries.append(entry)
            continue
        if not isinstance(doc, dict):
            entry["problem"] = "NOT_AN_OBJECT"
        else:
            entry["doc"] = doc
        entries.append(entry)
    return entries


def apply_binding_rule(entries, season):
    """Apply the contract binding rule; return (bound entry or None, census list)."""
    census = []
    eligible = []
    for entry in entries:
        doc = entry["doc"]
        summary = {"directory": entry["dir"], "sha256": entry["sha256"], "problem": entry["problem"]}
        if doc is None:
            summary["eligible"] = False
            census.append(summary)
            continue
        captures = doc.get("captures")
        count = doc.get("team_page_capture_count")
        reasons = []
        if doc.get("state") != "COMPLETE_GRAPH_EXHAUSTED":
            reasons.append("STATE_%s" % doc.get("state"))
        if doc.get("discovery_identity") != entry["dir"]:
            reasons.append("IDENTITY_MISMATCH")
        if not isinstance(captures, list) or isinstance(count, bool) or count != len(captures):
            reasons.append("CAPTURE_COUNT_MISMATCH")
        summary.update(state=doc.get("state"), captures=len(captures) if isinstance(captures, list) else None,
                       issued_at_utc=doc.get("issued_at_utc"), season_field=doc.get("season"),
                       eligible=not reasons, ineligible_reasons=reasons)
        census.append(summary)
        if not reasons:
            eligible.append(entry)
    if not eligible:
        return None, census
    most = max(len(entry["doc"]["captures"]) for entry in eligible)
    top = [entry for entry in eligible if len(entry["doc"]["captures"]) == most]
    if len(top) > 1:
        instants = [(parse_instant(entry["doc"].get("issued_at_utc")), entry) for entry in top]
        if any(instant is None for instant, _ in instants):
            raise Refusal("REFUSED_UNBREAKABLE_TIE",
                          "season %d: tied manifests with an unparseable or naive issued_at_utc" % season)
        latest = max(instant for instant, _ in instants)
        top = [entry for instant, entry in instants if instant == latest]
        if len(top) > 1:
            raise Refusal("REFUSED_UNBREAKABLE_TIE", "season %d: %s" % (season, [e["dir"] for e in top]))
    return top[0], census


def load_bound_manifests(ctx, seasons, check):
    """Load bound discovery manifests: delivery seasons from the contract (verified), 2015 by the rule."""
    bound = contract_section(ctx, "input_bindings", "bound_manifests")
    result = {}
    for season in seasons:
        if season == ADJACENT_SEASON:
            entry, _ = apply_binding_rule(discovery_entries(ctx, season), season)
            if entry is None:
                raise Refusal("INPUT_BINDING_MISMATCH", "no eligible %d discovery manifest" % season)
            result[season] = {"identity": entry["dir"], "sha256": entry["sha256"], "doc": entry["doc"]}
            continue
        expect = bound.get(str(season))
        if not isinstance(expect, dict):
            raise Refusal("CONTRACT_MALFORMED", "bound_manifests has no %d entry" % season)
        path = ctx.data_root.joinpath(*DISCOVERY_PARTS, str(season), "sha256", str(expect.get("identity")),
                                      DISCOVERY_FILE)
        if not path.is_file():
            raise Refusal("INPUT_MISSING", "bound manifest %s is missing" % path)
        raw = path.read_bytes()
        digest = sha256_bytes(raw)
        if digest != expect.get("sha256"):
            raise Refusal("INPUT_BINDING_MISMATCH", "bound manifest %d sha256 %s != %s"
                          % (season, digest, expect.get("sha256")))
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise Refusal("INPUT_MALFORMED", "bound manifest %d is not JSON" % season)
        if doc.get("discovery_identity") != expect.get("identity") or len(doc.get("captures") or []) != expect.get(
                "captures"):
            raise Refusal("INPUT_BINDING_MISMATCH", "bound manifest %d identity/captures differ" % season)
        result[season] = {"identity": expect.get("identity"), "sha256": digest, "doc": doc}
    check.counts["bound_manifests"] = {
        str(season): {"identity": info["identity"], "captures": len(info["doc"].get("captures") or []),
                      "failures": len(info["doc"].get("failures") or [])}
        for season, info in sorted(result.items())
    }
    return result


def load_pages(ctx, manifests):
    """Read every bound capture once: rehash and parse.  Returns {(season, team_season_id): page}."""
    pages = {}
    for season, info in sorted(manifests.items()):
        for capture in info["doc"].get("captures") or []:
            ts = str(capture.get("team_season_id"))
            relative = capture.get("raw_relative_path") or ""
            declared = capture.get("raw_sha256")
            record = {"season": season, "ts": ts, "raw_relative_path": relative, "raw_sha256": declared,
                      "exists": False, "rehash_ok": False, "name_ok": False, "parsed": None}
            path = data_path(ctx, relative)
            if path.is_file():
                record["exists"] = True
                data = path.read_bytes()
                record["rehash_ok"] = sha256_bytes(data) == declared
                record["name_ok"] = path.name == "%s.html" % declared
                if record["rehash_ok"]:
                    record["parsed"] = parse_team_season_page(data.decode("utf-8", errors="replace"))
            parsed = record["parsed"]
            if parsed is not None:
                record["identity_ok"] = parsed["selected"] == (season_label(season), ts)
            else:
                record["identity_ok"] = False
            pages[(season, ts)] = record
    return pages


def load_team_history(ctx, check):
    root_rel = contract_section(ctx, "input_bindings", "team_history_root", "path")
    root = data_path(ctx, root_rel)
    if not root.is_dir():
        raise Refusal("INPUT_MISSING", "team-history directory %s is missing" % root)
    rows_by_key = {}
    conflicts = []
    pages_with_table = 0
    pages_without_table = 0
    skipped = collections.Counter()
    identical_duplicates = 0
    for path in sorted(root.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="replace")
        org, rows = parse_team_history_page(text)
        if rows is None:
            pages_without_table += 1
            continue
        pages_with_table += 1
        if org is None:
            skipped["PAGE_WITHOUT_ORG_ID"] += len(rows)
            continue
        for row in rows:
            if row["malformed"]:
                skipped[row["kind"]] += 1
                continue
            if not row["label_ok"]:
                skipped["SEASON_LABEL_NOT_Y_YY"] += 1
                continue
            key = (org, row["season"])
            value = {k: row[k] for k in ("team_season_id", "division", "conference", "wins", "losses", "ties",
                                         "pct", "notes")}
            if key in rows_by_key:
                if rows_by_key[key]["value"] == value:
                    identical_duplicates += 1
                else:
                    conflicts.append({"org": org, "season": row["season"], "kept": rows_by_key[key]["value"],
                                      "other": value, "page": path.name})
                continue
            rows_by_key[key] = {"value": value, "page": path.name}
    check.counts["team_history"] = {"pages_with_table": pages_with_table, "pages_without_table": pages_without_table,
                                    "skipped_rows": counter_dict(skipped), "identical_duplicates": identical_duplicates,
                                    "conflicting_duplicates_all_seasons": len(conflicts),
                                    "org_season_rows_all_seasons": len(rows_by_key)}
    return rows_by_key, conflicts


# ------------------------------------------------------------------------------- manifest verification


def verify_stage_manifest(ctx, manifest_path, expected_stage, check, role):
    path = pathlib.Path(manifest_path)
    if not path.is_file():
        raise Refusal("MANIFEST_MISSING", "%s manifest %s does not exist" % (role, path))
    id_dir = path.parent
    sha_dir = id_dir.parent
    population_dir = sha_dir.parent
    manifests_dir = population_dir.parent
    root = manifests_dir.parent
    if path.name != "run_manifest.json" or sha_dir.name != "sha256" or manifests_dir.name != "manifests":
        raise Refusal("MANIFEST_PATH_MALFORMED", "%s manifest path %s is not <X>/manifests/<population>/sha256/<id>/"
                      "run_manifest.json" % (role, path))
    try:
        manifest = json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refusal("MANIFEST_MALFORMED", "%s manifest is not JSON (%s)" % (role, exc))
    if not isinstance(manifest, dict) or any(key not in manifest for key in MANIFEST_KEYS):
        raise Refusal("MANIFEST_MALFORMED", "%s manifest lacks keys %s" % (role, MANIFEST_KEYS))
    doc = manifest["identity_document"]
    if not isinstance(doc, dict) or any(key not in doc for key in IDENTITY_DOCUMENT_KEYS):
        raise Refusal("MANIFEST_MALFORMED", "%s identity_document lacks keys %s" % (role, IDENTITY_DOCUMENT_KEYS))
    computed = canonical_sha256(doc)
    if computed != id_dir.name or manifest["identity"] != id_dir.name:
        raise Refusal("MANIFEST_IDENTITY_MISMATCH", "%s identity: directory %s, identity %s, canonical sha256 %s"
                      % (role, id_dir.name, manifest["identity"], computed))
    if role == "stage":
        ctx.manifest_identity = id_dir.name
    if doc["population"] != POPULATION or population_dir.name != POPULATION:
        raise Refusal("MANIFEST_IDENTITY_MISMATCH", "%s population %s / directory %s != %s"
                      % (role, doc["population"], population_dir.name, POPULATION))
    if doc["stage"] != expected_stage:
        raise Refusal("MANIFEST_STAGE_MISMATCH", "%s stage %s != %s" % (role, doc["stage"], expected_stage))
    if doc["contract_sha256"] != ctx.contract_sha256:
        raise Refusal("CONTRACT_IDENTITY_MISMATCH", "%s identity_document.contract_sha256 %s != presented contract %s"
                      % (role, doc["contract_sha256"], ctx.contract_sha256))
    outputs = doc["outputs"]
    if not isinstance(outputs, dict) or not outputs:
        raise Refusal("MANIFEST_MALFORMED", "%s outputs is not a non-empty object" % role)
    canonical_dir = root / "canonical" / population_dir.name / "sha256" / id_dir.name
    if not canonical_dir.is_dir():
        raise Refusal("OUTPUT_MISSING", "%s canonical directory %s is missing" % (role, canonical_dir))
    data = {}
    for name, declared in sorted(outputs.items()):
        if not isinstance(name, str) or "/" in name or "\\" in name or name in ("", ".", ".."):
            raise Refusal("MANIFEST_MALFORMED", "%s output name %r is not a plain file name" % (role, name))
        file_path = canonical_dir / name
        if not file_path.is_file():
            raise Refusal("OUTPUT_MISSING", "%s output %s is missing" % (role, name))
        raw = file_path.read_bytes()
        digest = sha256_bytes(raw)
        if digest != declared:
            raise Refusal("OUTPUT_HASH_MISMATCH", "%s output %s sha256 %s != declared %s"
                          % (role, name, digest, declared))
        data[name] = raw
    present = sorted(p.name for p in canonical_dir.iterdir())
    undeclared = [name for name in present if name not in outputs]
    if undeclared:
        raise Refusal("OUTPUT_SET_MISMATCH", "%s canonical directory holds undeclared files %s" % (role, undeclared))
    headers = {}
    for name, raw in sorted(data.items()):
        header = None
        if name.endswith(".jsonl.gz"):
            try:
                with gzip.open(canonical_dir / name, "rt", encoding="utf-8") as handle:
                    first = json.loads(handle.readline())
            except (OSError, EOFError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise Refusal("OUTPUT_MALFORMED", "%s output %s first line unreadable (%s)" % (role, name, exc))
            if not isinstance(first, dict) or not isinstance(first.get("_header"), dict):
                raise Refusal("OUTPUT_MALFORMED", "%s output %s has no _header first line" % (role, name))
            header = first["_header"]
            for key in ("schema", "stage", "contract_sha256"):
                if key not in header:
                    raise Refusal("OUTPUT_MALFORMED", "%s output %s header lacks %s" % (role, name, key))
        elif name.endswith(".json"):
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise Refusal("OUTPUT_MALFORMED", "%s output %s is not JSON (%s)" % (role, name, exc))
            if isinstance(parsed, dict) and isinstance(parsed.get("_header"), dict):
                header = parsed["_header"]
        if header is None:
            continue
        headers[name] = header
        if header.get("contract_sha256") != ctx.contract_sha256:
            raise Refusal("CONTRACT_IDENTITY_MISMATCH", "%s output %s header contract_sha256 %s != presented %s"
                          % (role, name, header.get("contract_sha256"), ctx.contract_sha256))
        if "stage" in header and header["stage"] != doc["stage"]:
            raise Refusal("OUTPUT_HEADER_MISMATCH", "%s output %s header stage %s != %s"
                          % (role, name, header["stage"], doc["stage"]))
        if "schema" in header and header["schema"] != doc["schema"]:
            raise Refusal("OUTPUT_HEADER_MISMATCH", "%s output %s header schema %s != %s"
                          % (role, name, header["schema"], doc["schema"]))
    check.counts["%s_manifest" % role] = {"identity": id_dir.name, "stage": doc["stage"], "outputs": len(outputs),
                                         "headers_checked": len(headers), "issued_at_utc": manifest["issued_at_utc"]}
    return {"manifest": manifest, "doc": doc, "identity": id_dir.name, "canonical_dir": canonical_dir,
            "data": data, "headers": headers, "path": path}


def require_output(info, name):
    if name not in info["data"]:
        raise Refusal("OUTPUT_MISSING", "stage %s does not declare required output %s" % (info["identity"], name))
    return info["data"][name]


def load_json_output(info, name):
    try:
        return json.loads(require_output(info, name).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refusal("OUTPUT_MALFORMED", "%s is not JSON (%s)" % (name, exc))


def load_jsonl_output(info, name):
    return read_jsonl_gz_bytes(require_output(info, name), name)


def verify_upstream(ctx, info, check):
    upstream = info["doc"].get("upstream")
    if not isinstance(upstream, dict) or not isinstance(upstream.get("program-season"), str):
        raise Refusal("UPSTREAM_MISSING", "contest manifest names no upstream program-season identity")
    m1_id = upstream["program-season"]
    m1_path = info["path"].parent.parent / m1_id / "run_manifest.json"
    m1 = verify_stage_manifest(ctx, m1_path, "program-season", check, "upstream")
    for name, header in info["headers"].items():
        if "program_season_identity" in header and header["program_season_identity"] != m1_id:
            raise Refusal("UPSTREAM_IDENTITY_MISMATCH", "output %s header program_season_identity %s != %s"
                          % (name, header["program_season_identity"], m1_id))
    return m1


def check_row_counts(ctx, info, actual):
    check = ctx.check("manifest_row_counts")
    declared = info["manifest"].get("row_counts")
    if not isinstance(declared, dict):
        check.disagree({"field": "row_counts", "problem": "not an object"})
        return
    for key, count in sorted(actual.items()):
        check.counts[key] = {"declared": declared.get(key), "rows": count}
        if declared.get(key) != count:
            check.disagree({"stage": info["doc"]["stage"], "row_count": key, "manifest": declared.get(key),
                            "validator_rows": count})


# ------------------------------------------------------------------------------------------ stage: inputs


def stage_inputs(ctx):
    bindings = contract_section(ctx, "input_bindings")
    seasons = delivery_seasons(ctx)
    bound_contract = contract_section(ctx, "input_bindings", "bound_manifests")

    check = ctx.check("manifest_binding")
    all_entries = {}
    bound = {}
    per_season = {}
    discovery_root = ctx.data_root.joinpath(*DISCOVERY_PARTS)
    if not discovery_root.is_dir():
        raise Refusal("INPUT_MISSING", "discovery root %s is missing" % discovery_root)
    for season_dir in sorted(discovery_root.iterdir(), key=lambda p: p.name):
        if season_dir.is_dir() and season_dir.name.isdigit():
            all_entries[int(season_dir.name)] = discovery_entries(ctx, int(season_dir.name))
    for season in BINDING_SEASONS:
        entry, census = apply_binding_rule(all_entries.get(season, []), season)
        per_season[str(season)] = {
            "manifests": len(census),
            "eligible": sum(1 for row in census if row.get("eligible")),
            "bound_identity": entry["dir"] if entry else None,
            "bound_sha256": entry["sha256"] if entry else None,
            "bound_captures": len(entry["doc"]["captures"]) if entry else None,
            "bound_issued_at_utc": entry["doc"].get("issued_at_utc") if entry else None,
            "identity_mismatches": [row["directory"] for row in census if "IDENTITY_MISMATCH" in
                                    (row.get("ineligible_reasons") or [])],
        }
        if entry is None:
            check.disagree({"season": season, "problem": "NO_ELIGIBLE_MANIFEST"})
            continue
        bound[season] = entry
        if entry["doc"].get("season") != season:
            check.disagree({"season": season, "problem": "BOUND_MANIFEST_SEASON_FIELD", "value":
                            entry["doc"].get("season")})
        if season in seasons:
            expect = bound_contract.get(str(season)) or {}
            mine = {"identity": entry["dir"], "sha256": entry["sha256"], "captures": len(entry["doc"]["captures"])}
            for key in ("identity", "sha256", "captures"):
                if mine[key] != expect.get(key):
                    check.disagree({"season": season, "field": key, "validator": mine[key],
                                    "contract": expect.get(key)})
    total = sum(len(bound[s]["doc"]["captures"]) for s in seasons if s in bound)
    check.counts["per_season"] = per_season
    check.counts["total_bound_captures_2016_2025"] = total
    check.counts["contract_total_bound_captures"] = bindings.get("total_bound_captures")
    if total != bindings.get("total_bound_captures"):
        check.disagree({"field": "total_bound_captures", "validator": total,
                        "contract": bindings.get("total_bound_captures")})

    check = ctx.check("capture_rehash")
    rehashed = 0
    counts = collections.Counter()
    for season in seasons:
        if season not in bound:
            continue
        for capture in bound[season]["doc"]["captures"]:
            relative = capture.get("raw_relative_path") or ""
            declared = capture.get("raw_sha256")
            path = data_path(ctx, relative)
            counts["captures"] += 1
            if not relative.replace("\\", "/").startswith("/".join(SRC015_PARTS) + "/"):
                check.disagree({"season": season, "team_season_id": capture.get("team_season_id"),
                                "problem": "PATH_OUTSIDE_SRC015", "raw_relative_path": relative})
            if not path.is_file():
                check.disagree({"season": season, "team_season_id": capture.get("team_season_id"),
                                "problem": "FILE_MISSING", "raw_relative_path": relative})
                continue
            digest = sha256_file(path)
            rehashed += 1
            if digest != declared:
                check.disagree({"season": season, "team_season_id": capture.get("team_season_id"),
                                "problem": "SHA256_MISMATCH", "declared": declared, "actual": digest})
            if path.name != "%s.html" % declared:
                check.disagree({"season": season, "team_season_id": capture.get("team_season_id"),
                                "problem": "FILE_NAME_MISMATCH", "file": path.name, "declared": declared})
    check.counts["rehashed"] = rehashed
    check.counts["captures"] = counts["captures"]
    if rehashed != bindings.get("total_bound_captures"):
        check.disagree({"field": "rehashed", "validator": rehashed, "expected": bindings.get("total_bound_captures")})

    check = ctx.check("capture_failures")
    failures = {}
    for season in seasons:
        if season not in bound:
            continue
        doc = bound[season]["doc"]
        failure_ids = [str(f.get("team_season_id")) for f in doc.get("failures") or []]
        capture_ids = [str(c.get("team_season_id")) for c in doc.get("captures") or []]
        discovered = [str(x) for x in doc.get("discovered_team_season_ids") or []]
        failures[str(season)] = len(failure_ids)
        expected = SPEC_EXPECTED_FAILURES.get(season, 0)
        if len(failure_ids) != expected:
            check.disagree({"season": season, "failures": len(failure_ids), "spec_expected": expected})
        if set(capture_ids) | set(failure_ids) != set(discovered) or set(capture_ids) & set(failure_ids) \
                or len(set(discovered)) != len(discovered):
            check.disagree({"season": season, "problem": "DISCOVERED_NOT_CAPTURES_PLUS_FAILURES"})
        if doc.get("team_failure_count") != len(failure_ids):
            check.disagree({"season": season, "problem": "TEAM_FAILURE_COUNT", "field": doc.get(
                "team_failure_count"), "failures": len(failure_ids)})
    check.counts["failures_by_season"] = failures

    check = ctx.check("cfbd_fbs_route")
    routes = contract_section(ctx, "input_bindings", "cfbd_fbs_route")
    rows_by_season = {}
    for season in seasons:
        sha = routes.get(str(season))
        path = ctx.data_root.joinpath(*SRC002_GAMES_PARTS, "sha256_%s.json" % sha)
        if not path.is_file():
            check.disagree({"season": season, "problem": "FILE_MISSING", "file": path.name})
            continue
        raw = path.read_bytes()
        digest = sha256_bytes(raw)
        if digest != sha or path.name != "sha256_%s.json" % digest:
            check.disagree({"season": season, "problem": "SHA256_MISMATCH", "contract": sha, "actual": digest})
        try:
            rows = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            check.disagree({"season": season, "problem": "MALFORMED_JSON"})
            continue
        if not isinstance(rows, list):
            check.disagree({"season": season, "problem": "NOT_A_LIST"})
            continue
        rows_by_season[str(season)] = len(rows)
        other = sum(1 for row in rows if not isinstance(row, dict) or row.get("season") != season)
        if other:
            check.disagree({"season": season, "problem": "ROWS_OF_ANOTHER_SEASON", "rows": other})
    check.counts["rows_by_season"] = rows_by_season

    check = ctx.check("cycle30_fcs_route")
    ledger_info = contract_section(ctx, "input_bindings", "cycle30_ledger")
    fcs = contract_section(ctx, "input_bindings", "cfbd_fcs_route")
    ledger_path = data_path(ctx, ledger_info.get("path", ""))
    ledger = None
    if not ledger_path.is_file():
        check.disagree({"problem": "LEDGER_MISSING", "path": str(ledger_path)})
    else:
        raw = ledger_path.read_bytes()
        digest = sha256_bytes(raw)
        check.counts["ledger_sha256"] = digest
        if digest != ledger_info.get("sha256"):
            check.disagree({"problem": "LEDGER_SHA256_MISMATCH", "contract": ledger_info.get("sha256"),
                            "actual": digest})
        try:
            ledger = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            check.disagree({"problem": "LEDGER_MALFORMED"})
    reconciled = contract_section(ctx, "reconciliation", "two_source_seasons")
    fcs_rows = {}
    for season in reconciled:
        expect = fcs.get(str(season)) or {}
        attempts = [a for a in ((ledger or {}).get("attempts") or []) if isinstance(a, dict)
                    and a.get("route") == "/games" and a.get("parameters") == {"classification": "fcs", "year": season}]
        if len(attempts) != 1:
            check.disagree({"season": season, "problem": "LEDGER_ATTEMPTS", "matching_attempts": len(attempts)})
        path = ctx.data_root.joinpath(*CYCLE30_GAMES_PARTS, str(expect.get("file")))
        if not path.is_file():
            check.disagree({"season": season, "problem": "FILE_MISSING", "file": expect.get("file")})
            continue
        raw = path.read_bytes()
        digest = sha256_bytes(raw)
        if digest != expect.get("content_sha256"):
            check.disagree({"season": season, "problem": "CONTENT_SHA256_MISMATCH",
                            "contract": expect.get("content_sha256"), "actual": digest})
        try:
            rows = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            check.disagree({"season": season, "problem": "MALFORMED_JSON"})
            continue
        count = len(rows) if isinstance(rows, list) else None
        fcs_rows[str(season)] = count
        if len(attempts) == 1:
            attempt = attempts[0]
            if attempt.get("raw_sha256") != expect.get("content_sha256"):
                check.disagree({"season": season, "problem": "LEDGER_RAW_SHA256", "ledger": attempt.get("raw_sha256"),
                                "contract": expect.get("content_sha256")})
            if attempt.get("row_count") != count:
                check.disagree({"season": season, "problem": "LEDGER_ROW_COUNT", "ledger": attempt.get("row_count"),
                                "file_rows": count})
    check.counts["fcs_rows_by_season"] = fcs_rows

    check = ctx.check("bound_file_hashes")
    hashed = {}
    for key in ("cycle30_membership", "canonical_registry", "bat652_spine_membership",
                "fcs_expected_game_population_predecessor"):
        info = bindings.get(key) or {}
        path = bound_input_path(ctx, info.get("path", ""))
        if not path.is_file():
            check.disagree({"input": key, "problem": "FILE_MISSING", "path": str(path)})
            continue
        digest = sha256_file(path)
        hashed[key] = digest == info.get("sha256")
        if digest != info.get("sha256"):
            check.disagree({"input": key, "problem": "SHA256_MISMATCH", "contract": info.get("sha256"),
                            "actual": digest})
    current = bindings.get("current_2026_population") or {}
    current_path = ctx.repo_root.joinpath(*current.get("repository_path", "").split("/"))
    if not current_path.is_file():
        check.disagree({"input": "current_2026_population", "problem": "FILE_MISSING", "path": str(current_path)})
    else:
        digest = sha256_file(current_path)
        hashed["current_2026_population"] = digest == current.get("sha256")
        if digest != current.get("sha256"):
            check.disagree({"input": "current_2026_population", "problem": "SHA256_MISMATCH",
                            "contract": current.get("sha256"), "actual": digest})
    history = bindings.get("team_history_root") or {}
    history_dir = data_path(ctx, history.get("path", ""))
    file_count = sum(1 for p in history_dir.iterdir() if p.is_file()) if history_dir.is_dir() else None
    check.counts["team_history_file_count"] = file_count
    if file_count != history.get("file_count"):
        check.disagree({"input": "team_history_root", "problem": "FILE_COUNT", "contract": history.get("file_count"),
                        "actual": file_count})
    check.counts["sha256_ok"] = hashed

    check = ctx.check("unreferenced_src015")
    referenced = set()
    for season, entries in all_entries.items():
        for entry in entries:
            for capture in (entry["doc"] or {}).get("captures") or []:
                if isinstance(capture, dict) and capture.get("raw_relative_path"):
                    referenced.add(capture["raw_relative_path"].replace("\\", "/").rsplit("/", 1)[-1])
    src = ctx.data_root.joinpath(*SRC015_PARTS)
    files = sorted(p.name for p in src.iterdir() if p.is_file()) if src.is_dir() else []
    unreferenced = [name for name in files if name not in referenced]
    check.counts.update(src015_files=len(files), referenced_files=len(referenced & set(files)),
                        manifests_scanned=sum(len(v) for v in all_entries.values()),
                        unreferenced=len(unreferenced), unreferenced_head=unreferenced[:HEAD_LIMIT],
                        used_as_evidence=0)
    if len(unreferenced) != SPEC_EXPECTED_UNREFERENCED_SRC015:
        check.disagree({"field": "unreferenced", "validator": len(unreferenced),
                        "spec_expected": SPEC_EXPECTED_UNREFERENCED_SRC015})


# ---------------------------------------------------------------------------------- shared reconstruction


class Universe:
    """Independent reconstruction from bound pages, failures and official team-history rows."""

    def __init__(self, ctx, manifests, pages, history_rows):
        self.ctx = ctx
        self.manifests = manifests
        self.pages = pages
        self.seasons = delivery_seasons(ctx)
        self.discovered = {season: set(str(x) for x in info["doc"].get("discovered_team_season_ids") or [])
                           for season, info in manifests.items()}
        self.graph = collections.defaultdict(list)  # (org, season) -> [page]
        self.page_without_org = []
        for (season, ts), page in pages.items():
            parsed = page["parsed"]
            if parsed is None:
                continue
            if parsed["org_id"] is None:
                self.page_without_org.append(page)
                continue
            self.graph[(parsed["org_id"], season)].append(page)
        self.code = {}
        for (org, season), plist in self.graph.items():
            if len(plist) == 1 and plist[0]["parsed"]["decode_state"] == "DECODED":
                self.code[(org, season)] = plist[0]["parsed"]["code"]
        self.ts_code = {}
        for (season, ts), page in pages.items():
            parsed = page["parsed"]
            if parsed is not None and parsed["decode_state"] == "DECODED":
                self.ts_code[ts] = parsed["code"]
        self.history = {}
        for (org, season), entry in history_rows.items():
            self.history[(org, season)] = entry["value"]
        self.failures = collections.defaultdict(list)  # (org, season) -> [ts]
        self.unresolved_failures = []
        self._resolve_failures()

    def failure_ids(self, season):
        info = self.manifests.get(season)
        ids = [str(f.get("team_season_id")) for f in (info["doc"].get("failures") or [])] if info else []
        for (s, ts), page in self.pages.items():
            if s == season and page["parsed"] is None:
                ids.append(ts)  # rehash failures are payload-missing captures
        return ids

    def _resolve_failures(self):
        logo = collections.defaultdict(set)
        for page in self.pages.values():
            if page["parsed"] is None:
                continue
            for row in page["parsed"]["rows"]:
                if row.get("opp_ts") and row.get("opp_logo_org"):
                    logo[row["opp_ts"]].add(row["opp_logo_org"])
        self.failure_org_source = {}
        for season in self.seasons:
            label = season_label(season)
            for ts in self.failure_ids(season):
                orgs = set()
                for adjacent in (season - 1, season + 1):
                    for (s, _), page in self.pages.items():
                        if s != adjacent or page["parsed"] is None or page["parsed"]["org_id"] is None:
                            continue
                        if page["parsed"]["season_options"].get(label) == ts:
                            orgs.add(page["parsed"]["org_id"])
                source = "SEASON_SELECTOR_ADJACENT"
                if not orgs:
                    orgs = set(logo.get(ts, set()))
                    source = "OPPONENT_LOGO"
                if len(orgs) == 1:
                    org = next(iter(orgs))
                    self.failures[(org, season)].append(ts)
                    self.failure_org_source[(season, ts)] = (org, source)
                else:
                    self.unresolved_failures.append({"season": season, "team_season_id": ts,
                                                     "candidate_orgs": sorted(orgs)})

    def e1_keys(self):
        keys = set()
        for (org, season) in self.graph:
            if season in self.seasons:
                keys.add((org, season))
        for (org, season) in self.failures:
            keys.add((org, season))
        return keys

    def e2_keys(self):
        return {key for key in self.history if key[1] in self.seasons}

    def e4_keys(self):
        result = collections.defaultdict(set)  # (org, season) -> {ts}
        for season in self.seasons:
            label = season_label(season)
            discovered = self.discovered.get(season, set())
            for (s, _), page in self.pages.items():
                if s not in (season - 1, season + 1) or page["parsed"] is None or page["parsed"]["org_id"] is None:
                    continue
                ts = page["parsed"]["season_options"].get(label)
                if ts and ts not in discovered:
                    result[(page["parsed"]["org_id"], season)].add(ts)
        return result

    def history_label(self, org, season):
        row = self.history.get((org, season))
        if row is None or not row["division"]:
            return None
        return row["division"]


def page_code_label(ctx, code):
    table = contract_section(ctx, "division_decoding", "table")
    entry = table.get(code) if code is not None else None
    return entry.get("label") if isinstance(entry, dict) else None


def expected_cell(universe, org, season):
    """Re-derive the disposition of an organization-keyed cell from raw evidence."""
    plist = universe.graph.get((org, season), [])
    fails = universe.failures.get((org, season), [])
    label = universe.history_label(org, season)
    out = {"page": None, "failure": None, "history_label": label, "code": None, "disposition": None,
           "division_label": None, "reason": None}
    if len(plist) + len(fails) > 1:
        out["disposition"] = "AMBIGUOUS_MULTIPLE_SOURCES"
        return out
    if plist:
        page = plist[0]
        parsed = page["parsed"]
        out["page"] = page
        if parsed["decode_state"] != "DECODED":
            out["disposition"] = "IDENTITY_UNRESOLVED"
            out["code"] = None
            return out
        code = parsed["code"]
        out["code"] = code
        out["division_label"] = page_code_label(universe.ctx, code)
        if label is not None and HISTORY_LABEL_TO_CODE.get(label) != code:
            out["disposition"] = "CONFLICT"
            return out
        if code in ("11", "12"):
            if page["rehash_ok"] and page["identity_ok"] and parsed["header"] is not None:
                out["disposition"] = "VERIFIED_PRESENT"
            else:
                out["disposition"] = "UNSPECIFIED_DIVISION_I_PAGE_PROBLEM"
            return out
        out["disposition"] = "NOT_APPLICABLE"
        return out
    if fails:
        out["failure"] = fails[0]
        out["disposition"] = "PAYLOAD_MISSING"
        return out
    out["disposition"] = "SOURCE_ABSENT"
    out["division_label"] = label if label is not None else "UNKNOWN_NOT_PROJECTED"
    return out


def parse_cell_key(cell_key):
    if not isinstance(cell_key, str):
        return None
    parts = cell_key.split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        return None
    return parts[0], parts[1], int(parts[2])


# ---------------------------------------------------------------------------------- stage: program-season


def stage_program_season(ctx):
    seasons = delivery_seasons(ctx)
    verify = ctx.check("manifest_verification")
    info = verify_stage_manifest(ctx, ctx.manifest_path, "program-season", verify, "stage")
    ctx.manifest_identity = info["identity"]
    _, decode_rows = load_jsonl_output(info, "page_decode.jsonl.gz")
    _, cells = load_jsonl_output(info, "program_season_cells.jsonl.gz")
    summary = load_json_output(info, "season_summary.json")
    transitions_rows = None
    if "transitions.jsonl.gz" in info["data"]:
        _, transitions_rows = load_jsonl_output(info, "transitions.jsonl.gz")
    observation_diffs = load_json_output(info, "observation_diffs.json") if "observation_diffs.json" in info[
        "data"] else None
    check_row_counts(ctx, info, {"cells": len(cells), "pages": len(decode_rows)})

    inputs_check = ctx.check("manifest_inputs")
    manifests = load_bound_manifests(ctx, [ADJACENT_SEASON] + seasons, inputs_check)
    declared = (info["doc"].get("inputs") or {}).get("bound_manifests")
    if not isinstance(declared, dict):
        inputs_check.disagree({"field": "identity_document.inputs.bound_manifests", "problem": "absent"})
    else:
        for season, mine in sorted(manifests.items()):
            entry = declared.get(str(season)) or {}
            doc = mine["doc"]
            expect = {"identity": mine["identity"], "sha256": mine["sha256"], "captures": len(doc.get("captures") or []),
                      "failures": len(doc.get("failures") or []),
                      "discovered": len(doc.get("discovered_team_season_ids") or []),
                      "issued_at_utc": doc.get("issued_at_utc")}
            for key, value in expect.items():
                if entry.get(key) != value:
                    inputs_check.disagree({"season": season, "field": key, "validator": value,
                                           "producer": entry.get(key)})
        extra = sorted(set(declared) - {str(s) for s in manifests})
        if extra:
            inputs_check.disagree({"field": "bound_manifests", "unexpected_seasons": extra})

    pages = load_pages(ctx, manifests)
    history_rows, history_conflicts = load_team_history(ctx, inputs_check)
    delivery_conflicts = [c for c in history_conflicts if c["season"] in seasons]
    inputs_check.counts["team_history"]["conflicting_duplicates_2016_2025"] = len(delivery_conflicts)
    for conflict in delivery_conflicts:
        inputs_check.disagree({"problem": "TEAM_HISTORY_CONFLICTING_DUPLICATE", **conflict})
    universe = Universe(ctx, manifests, pages, history_rows)

    # ---- check 1: page decode
    check = ctx.check("page_decode")
    producer_pages = {}
    for row in decode_rows:
        key = (row.get("season"), str(row.get("team_season_id")))
        if key in producer_pages:
            check.disagree({"problem": "DUPLICATE_PRODUCER_ROW", "season": key[0], "team_season_id": key[1]})
        producer_pages[key] = row
    tallies = collections.defaultdict(collections.Counter)
    compared = 0
    for key, page in sorted(pages.items()):
        season, ts = key
        parsed = page["parsed"]
        code = parsed["code"] if parsed is not None and parsed["decode_state"] == "DECODED" else None
        tallies[season][code if code is not None else "none"] += 1
        row = producer_pages.get(key)
        if row is None:
            check.disagree({"problem": "MISSING_PRODUCER_ROW", "season": season, "team_season_id": ts,
                            "raw_sha256": page["raw_sha256"]})
            continue
        compared += 1
        mine = {"rehash_ok": page["rehash_ok"], "raw_sha256": page["raw_sha256"]}
        if parsed is not None:
            header = parsed["header"]
            mine.update({
                "org_id": parsed["org_id"],
                "decode_state": parsed["decode_state"],
                "code": parsed["code"] if parsed["decode_state"] == "DECODED" else None,
                "header_record": None if header is None else [header["wins"], header["losses"], header["ties"]],
                "identity_ok": page["identity_ok"],
                "selected_season_label": parsed["selected"][0] if parsed["selected"] else None,
                "schedule_rows": len(parsed["rows"]),
            })
        theirs = dict(row)
        record = row.get("header_record")
        theirs["header_record"] = None if record is None else [record.get("wins"), record.get("losses"),
                                                                record.get("ties")]
        if theirs.get("decode_state") != "DECODED":
            theirs["code"] = None
        for field, value in mine.items():
            if theirs.get(field) != value:
                check.disagree({"season": season, "team_season_id": ts, "field": field, "validator": value,
                                "producer": theirs.get(field), "raw_sha256": page["raw_sha256"]})
    for key in sorted(set(producer_pages) - set(pages), key=str):
        check.disagree({"problem": "UNEXPECTED_PRODUCER_ROW", "season": key[0], "team_season_id": key[1]})
    check.counts["pages_parsed"] = sum(1 for p in pages.values() if p["parsed"] is not None)
    check.counts["pages_bound"] = len(pages)
    check.counts["rehash_failures"] = sum(1 for p in pages.values() if not p["rehash_ok"])
    check.counts["identity_failures"] = sum(1 for p in pages.values() if p["parsed"] is not None
                                            and not p["identity_ok"])
    check.counts["pages_without_org"] = len(universe.page_without_org)
    check.counts["rows_compared"] = compared
    check.counts["code_tallies_by_season"] = {str(s): counter_dict(tallies[s]) for s in sorted(tallies)}
    states = collections.Counter(p["parsed"]["decode_state"] for p in pages.values() if p["parsed"] is not None)
    check.counts["decode_states"] = counter_dict(states)
    for season, expected in SPEC_EXPECTED_CODE_TALLIES.items():
        mine = {k: tallies[season].get(k, 0) for k in expected}
        if mine != expected:
            check.disagree({"season": season, "problem": "SPEC_EXPECTED_TALLY", "validator": mine,
                            "spec_expected": expected})
    summary_seasons = summary.get("seasons") if isinstance(summary, dict) else None
    for season in seasons:
        theirs = ((summary_seasons or {}).get(str(season)) or {}).get("graph_pages_by_code")
        mine = {("None" if k == "none" else k): v for k, v in tallies[season].items() if v}
        theirs_clean = {k: v for k, v in (theirs or {}).items() if v}
        if mine != theirs_clean:
            check.disagree({"season": season, "problem": "GRAPH_PAGES_BY_CODE", "validator": mine,
                            "producer": theirs})

    # ---- index producer cells
    by_key = collections.defaultdict(list)
    for cell in cells:
        by_key[cell.get("cell_key")].append(cell)

    # ---- check 2: expected keys
    check = ctx.check("expected_keys")
    e1 = universe.e1_keys()
    e2 = universe.e2_keys()
    e4 = universe.e4_keys()
    e4_keys = set(e4)
    independent = e1 | e2 | e4_keys
    check.counts.update(e1_keys=len(e1), e2_keys=len(e2), e4_keys=len(e4_keys), union_keys=len(independent),
                        failures_resolved=len(universe.failure_org_source),
                        failures_unresolved=len(universe.unresolved_failures),
                        failure_org_sources=counter_dict(collections.Counter(
                            src for _, src in universe.failure_org_source.values())))
    check.counts["by_season"] = {str(s): {"E1": sum(1 for k in e1 if k[1] == s), "E2": sum(1 for k in e2 if k[1] == s),
                                          "E4": sum(1 for k in e4_keys if k[1] == s),
                                          "union": sum(1 for k in independent if k[1] == s)} for s in seasons}
    for item in universe.unresolved_failures:
        key = "ts:%s:%d" % (item["team_season_id"], item["season"])
        if len(by_key.get(key, [])) != 1:
            check.disagree({"problem": "UNRESOLVED_FAILURE_CELL", "cell_key": key, "producer_rows":
                            len(by_key.get(key, [])), "candidate_orgs": item["candidate_orgs"]})
    for org, season in sorted(independent, key=lambda k: (k[1], k[0])):
        key = "org:%s:%d" % (org, season)
        found = by_key.get(key, [])
        if len(found) != 1:
            check.disagree({"cell_key": key, "problem": "EXPECTED_KEY_NOT_EXACTLY_ONCE", "producer_rows": len(found),
                            "sources": [s for s, ks in (("E1", e1), ("E2", e2), ("E4", e4_keys)) if (org, season) in ks]})
    source_mismatch = 0
    for cell in cells:
        parsed_key = parse_cell_key(cell.get("cell_key"))
        if parsed_key is None or parsed_key[0] != "org":
            continue
        key = (parsed_key[1], parsed_key[2])
        sources = set(cell.get("expected_sources") or [])
        for name, keyset in (("E1", e1), ("E2", e2), ("E4", e4_keys)):
            if (name in sources) != (key in keyset):
                source_mismatch += 1
                check.disagree({"cell_key": cell.get("cell_key"), "problem": "EXPECTED_SOURCE_MEMBERSHIP",
                                "source": name, "validator": key in keyset, "producer": name in sources})
    check.counts["expected_source_membership_mismatches"] = source_mismatch
    outside = 0
    for cell in cells:
        parsed_key = parse_cell_key(cell.get("cell_key"))
        if parsed_key is not None and parsed_key[0] == "org" and (parsed_key[1], parsed_key[2]) not in independent:
            outside += 1
    check.counts["producer_org_cells_outside_e1_e2_e4"] = outside

    # ---- check 3: dispositions
    check = ctx.check("dispositions")
    derived = collections.Counter()
    for cell in cells:
        cell_key = cell.get("cell_key")
        parsed_key = parse_cell_key(cell_key)
        if cell.get("provider_key") is not None:
            derived["provider_key_cells"] += 1
            if cell.get("disposition") != "IDENTITY_UNRESOLVED":
                check.disagree({"cell_key": cell_key, "rule": "PROVIDER_KEY_MUST_BE_IDENTITY_UNRESOLVED",
                                "producer": cell.get("disposition")})
            continue
        if parsed_key is None:
            check.disagree({"cell_key": cell_key, "problem": "MALFORMED_CELL_KEY"})
            continue
        kind, ident, season = parsed_key
        if kind == "ts":
            derived["ts_cells"] += 1
            if cell.get("disposition") != "PAYLOAD_MISSING":
                check.disagree({"cell_key": cell_key, "rule": "UNRESOLVED_FAILURE_PAYLOAD_MISSING",
                                "producer": cell.get("disposition")})
            continue
        if kind != "org":
            derived["other_cells"] += 1
            if cell.get("disposition") != "IDENTITY_UNRESOLVED":
                check.disagree({"cell_key": cell_key, "rule": "PROVIDER_KEYED_CELL_IDENTITY_UNRESOLVED",
                                "producer": cell.get("disposition")})
            continue
        expect = expected_cell(universe, ident, season)
        derived[expect["disposition"]] += 1
        problems = []
        if cell.get("disposition") != expect["disposition"]:
            problems.append(("disposition", expect["disposition"], cell.get("disposition")))
        page = expect["page"]
        if page is not None:
            graph_page = cell.get("graph_page") or {}
            if graph_page.get("raw_sha256") != page["raw_sha256"]:
                problems.append(("graph_page.raw_sha256", page["raw_sha256"], graph_page.get("raw_sha256")))
            if cell.get("ncaa_team_season_id") != page["ts"]:
                problems.append(("ncaa_team_season_id", page["ts"], cell.get("ncaa_team_season_id")))
            if cell.get("division_code_observed") != expect["code"]:
                problems.append(("division_code_observed", expect["code"], cell.get("division_code_observed")))
            if expect["code"] is not None and cell.get("division_label") != expect["division_label"]:
                problems.append(("division_label", expect["division_label"], cell.get("division_label")))
            if cell.get("division_authority") not in ("GRAPH_PAGE",) and expect["code"] is not None:
                problems.append(("division_authority", "GRAPH_PAGE", cell.get("division_authority")))
            header = page["parsed"]["header"]
            if header is not None and expect["code"] is not None:
                text = "%d-%d" % (header["wins"], header["losses"]) + (
                    "-%d" % header["ties"] if header["ties"] is not None else "")
                if cell.get("header_record_wlt") != text:
                    problems.append(("header_record_wlt", text, cell.get("header_record_wlt")))
        else:
            if cell.get("graph_page") is not None:
                problems.append(("graph_page", None, "present"))
            if cell.get("division_code_observed") is not None:
                problems.append(("division_code_observed", None, cell.get("division_code_observed")))
        if expect["failure"] is not None and cell.get("ncaa_team_season_id") != expect["failure"]:
            problems.append(("ncaa_team_season_id", expect["failure"], cell.get("ncaa_team_season_id")))
        if expect["disposition"] == "SOURCE_ABSENT":
            if cell.get("division_label") != expect["division_label"]:
                problems.append(("division_label", expect["division_label"], cell.get("division_label")))
            authority = "OFFICIAL_TEAM_HISTORY_ROW" if expect["history_label"] is not None else "NONE"
            if cell.get("division_authority") != authority:
                problems.append(("division_authority", authority, cell.get("division_authority")))
        disposition = cell.get("disposition")
        if disposition == "VERIFIED_PRESENT" and cell.get("in_division_i_population") is not True:
            problems.append(("in_division_i_population", True, cell.get("in_division_i_population")))
        if disposition == "NOT_APPLICABLE" and cell.get("in_division_i_population") is not False:
            problems.append(("in_division_i_population", False, cell.get("in_division_i_population")))
        if disposition in ("IDENTITY_UNRESOLVED", "PAYLOAD_MISSING") and cell.get("in_division_i_population") is True:
            problems.append(("in_division_i_population", "not true", True))
        for field, mine, theirs in problems:
            item = {"cell_key": cell_key, "field": field, "validator": mine, "producer": theirs}
            if page is not None:
                item["raw_sha256"] = page["raw_sha256"]
                item["raw_codes"] = page["parsed"]["raw_codes"]
            if expect["history_label"] is not None:
                item["team_history_label"] = expect["history_label"]
            check.disagree(item)
    check.counts["derived_dispositions"] = counter_dict(derived)
    check.counts["cells"] = len(cells)

    # ---- check 4: decoding proof
    check = ctx.check("decoding_proof")
    overlap = collections.Counter()
    agreement = collections.Counter()
    for (org, season), row in sorted(universe.history.items()):
        if season not in seasons or row["division"] not in PROOF_LABELS:
            continue
        code = universe.code.get((org, season))
        if code is None:
            continue
        overlap[row["division"]] += 1
        if HISTORY_LABEL_TO_CODE[row["division"]] == code:
            agreement[row["division"]] += 1
        else:
            check.disagree({"org": org, "season": season, "team_history_label": row["division"], "page_code": code,
                            "raw_sha256": universe.graph[(org, season)][0]["raw_sha256"]})
    code3_overlap = sum(1 for (org, season), row in universe.history.items()
                        if season in seasons and row["division"] and universe.code.get((org, season)) == "3")
    total = sum(overlap.values())
    check.counts.update(overlap_total=total, overlap_by_label=counter_dict(overlap),
                        agreement_by_label=counter_dict(agreement), code_3_overlaps_with_any_label=code3_overlap)
    mine = {"total": total, "FBS": overlap.get("FBS", 0), "FCS": overlap.get("FCS", 0), "D-II": overlap.get("D-II", 0)}
    if mine != SPEC_EXPECTED_DECODING_PROOF:
        check.disagree({"problem": "SPEC_EXPECTED_OVERLAP", "validator": mine,
                        "spec_expected": SPEC_EXPECTED_DECODING_PROOF})
    proof = (observation_diffs or {}).get("decoding_proof_against_team_history") if isinstance(
        observation_diffs, dict) else None
    if isinstance(proof, dict):
        theirs = {"overlap_total": proof.get("overlap_total"), "overlap_by_label": proof.get("overlap_by_label"),
                  "agreement_by_label": proof.get("agreement_by_label")}
        ours = {"overlap_total": total, "overlap_by_label": dict(overlap), "agreement_by_label": dict(agreement)}
        if theirs != ours:
            check.disagree({"problem": "PRODUCER_DECODING_PROOF", "validator": ours, "producer": theirs})

    # ---- check 5: totals
    check = ctx.check("totals")
    vocabulary = set(contract_section(ctx, "program_season_dispositions"))
    duplicates = [key for key, rows in by_key.items() if len(rows) > 1]
    for key in duplicates:
        check.disagree({"problem": "DUPLICATE_CELL_KEY", "cell_key": key, "rows": len(by_key[key])})
    recount = collections.defaultdict(lambda: {"cells": 0, "by_disposition": collections.Counter(),
                                               "division_i": collections.Counter()})
    for cell in cells:
        disposition = cell.get("disposition")
        if not isinstance(disposition, str) or disposition not in vocabulary:
            check.disagree({"problem": "DISPOSITION_NOT_IN_VOCABULARY", "cell_key": cell.get("cell_key"),
                            "disposition": disposition})
        season = cell.get("season")
        parsed_key = parse_cell_key(cell.get("cell_key"))
        if season not in seasons or parsed_key is None or parsed_key[2] != season:
            check.disagree({"problem": "CELL_SEASON", "cell_key": cell.get("cell_key"), "season": season})
        bucket = recount[season]
        bucket["cells"] += 1
        bucket["by_disposition"][disposition] += 1
        if cell.get("division_label") in DIVISION_I_HISTORY_LABELS:
            bucket["division_i"]["%s|%s" % (cell.get("division_label"), disposition)] += 1
    for season in seasons:
        theirs = (summary_seasons or {}).get(str(season))
        if not isinstance(theirs, dict):
            check.disagree({"season": season, "problem": "SUMMARY_SEASON_MISSING"})
            continue
        bucket = recount[season]
        for field, mine in (("cells", bucket["cells"]), ("by_disposition", dict(bucket["by_disposition"])),
                            ("division_i_by_label_and_disposition", dict(bucket["division_i"]))):
            value = theirs.get(field)
            if isinstance(value, dict):
                value = {k: v for k, v in value.items() if v}
            if value != mine:
                check.disagree({"season": season, "field": field, "validator_from_cells": mine, "summary": value})
    check.counts["cells_by_season"] = {str(s): recount[s]["cells"] for s in seasons}
    check.counts["duplicate_cell_keys"] = len(duplicates)
    extra = sorted(set((summary_seasons or {})) - {str(s) for s in seasons})
    if extra:
        check.disagree({"problem": "SUMMARY_SEASONS_OUTSIDE_SCOPE", "seasons": extra})

    # ---- check 6: transitions
    check = ctx.check("transitions")
    mine = {}
    for (org, season), code in universe.code.items():
        if season in seasons and season - 1 in seasons:
            before = universe.code.get((org, season - 1))
            if before is not None and before != code:
                mine[(org, season)] = (before, code)
    flagged = set()
    for cell in cells:
        parsed_key = parse_cell_key(cell.get("cell_key"))
        if cell.get("transition_observed") is True and parsed_key is not None:
            flagged.add((parsed_key[1], parsed_key[2]))
    for key in sorted(set(mine) | flagged, key=lambda k: (k[1], k[0])):
        if (key in mine) != (key in flagged):
            check.disagree({"org": key[0], "season": key[1], "validator": mine.get(key),
                            "producer_transition_observed": key in flagged})
    if transitions_rows is not None:
        rows = {}
        for row in transitions_rows:
            rows[(str(row.get("ncaa_org_id")), row.get("season"))] = (row.get("from_code"), row.get("to_code"))
        for key in sorted(set(mine) | set(rows), key=lambda k: (str(k[1]), k[0])):
            if mine.get(key) != rows.get(key):
                check.disagree({"org": key[0], "season": key[1], "validator": mine.get(key),
                                "producer_transitions_row": rows.get(key)})
    check.counts["transitions"] = len(mine)
    check.counts["by_season"] = counter_dict(collections.Counter(k[1] for k in mine))


# ----------------------------------------------------------------------------------------- stage: contest


def load_cfbd_union(ctx, check):
    seasons = contract_section(ctx, "reconciliation", "two_source_seasons")
    fbs = contract_section(ctx, "input_bindings", "cfbd_fbs_route")
    fcs = contract_section(ctx, "input_bindings", "cfbd_fcs_route")
    games = {}
    route_conflicts = []
    per_season = {}
    for season in seasons:
        sources = [("SRC-002", ctx.data_root.joinpath(*SRC002_GAMES_PARTS, "sha256_%s.json" % fbs.get(str(season))),
                    fbs.get(str(season))),
                   ("CYCLE30_FCS", ctx.data_root.joinpath(*CYCLE30_GAMES_PARTS, str((fcs.get(str(season)) or {}).get(
                       "file"))), (fcs.get(str(season)) or {}).get("content_sha256"))]
        count = 0
        for route, path, sha in sources:
            if not path.is_file():
                raise Refusal("INPUT_MISSING", "CFBD %s file for %d is missing (%s)" % (route, season, path))
            raw = path.read_bytes()
            if sha256_bytes(raw) != sha:
                raise Refusal("INPUT_HASH_MISMATCH", "CFBD %s file for %d does not hash to %s" % (route, season, sha))
            try:
                rows = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise Refusal("INPUT_MALFORMED", "CFBD %s file for %d is not JSON" % (route, season))
            for row in rows:
                if not isinstance(row, dict) or row.get("id") is None:
                    continue
                gid = str(row["id"])
                game = {"id": gid, "season": season, "season_field": row.get("season"),
                        "start": row.get("startDate"), "home": str(row.get("homeId")), "away": str(row.get("awayId")),
                        "home_points": row.get("homePoints"), "away_points": row.get("awayPoints"),
                        "home_class": row.get("homeClassification"), "away_class": row.get("awayClassification"),
                        "neutral": row.get("neutralSite"), "routes": [route]}
                if gid in games:
                    old = games[gid]
                    same = all(old[k] == game[k] for k in ("season", "start", "home", "away", "home_points",
                                                           "away_points"))
                    if not same:
                        route_conflicts.append({"cfbd_game_id": gid, "season": season})
                    old["routes"].append(route)
                    continue
                games[gid] = game
                count += 1
        per_season[str(season)] = count
    check.counts["cfbd_union_games_by_season"] = per_season
    check.counts["cfbd_route_conflicts"] = len(route_conflicts)
    return games, route_conflicts


def utc_date(value):
    instant = parse_instant(value)
    if instant is None:
        return None
    return instant.astimezone(datetime.timezone.utc).date()


RE_MARKER_SPLIT = re.compile(r"[^A-Z0-9_]+")


def has_marker(value, marker):
    """True when ``marker`` is a whole token of a string, or of any string nested in a list/dict."""
    if isinstance(value, str):
        return marker in RE_MARKER_SPLIT.split(value.upper())
    if isinstance(value, dict):
        return any(has_marker(k, marker) or has_marker(v, marker) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(has_marker(item, marker) for item in value)
    return False


def marks_not_one_to_one(contest):
    """Read the contest row's own reconciliation markers (disposition_reason, flags, conflict_fields)."""
    return any(has_marker(contest.get(field), "NOT_ONE_TO_ONE")
               for field in ("disposition_reason", "flags", "conflict_fields"))


def wlt(counter):
    return (counter.get("W", 0), counter.get("L", 0), counter.get("T", 0))


def build_independent_contests(pages):
    """Linked contests from every bound page row and grouped no-link contests."""
    linked = collections.defaultdict(list)
    nolink = collections.defaultdict(list)
    for (season, ts), page in pages.items():
        parsed = page["parsed"]
        if parsed is None:
            continue
        for row in parsed["rows"]:
            if row.get("contest_id"):
                linked[row["contest_id"]].append((page, row))
            else:
                opp = row["opp_ts"] if row.get("opp_ts") else "EXT:" + name_key(row.get("opp_name"))
                key = (season, row.get("date"), frozenset((ts, opp)))
                nolink[key].append((page, row))
    contests = {}
    for cid, observations in linked.items():
        contests[cid] = summarize_observations(observations)
    nolink_contests = {key: summarize_observations(obs) for key, obs in nolink.items()}
    return contests, nolink_contests


def summarize_observations(observations):
    participants = set()
    points = {}
    score_conflict = False
    neutral = False
    home_claims = set()
    seasons = set()
    dates = set()
    statuses = set()
    names = {}
    for page, row in observations:
        team = page["ts"]
        opp = row["opp_ts"] if row.get("opp_ts") else "EXT"
        if opp == "EXT":
            names["EXT"] = row.get("opp_name")
        participants.add(team)
        participants.add(opp)
        seasons.add(page["season"])
        dates.add(row.get("date"))
        statuses.add(row.get("status"))
        if row.get("p") is not None:
            for side, value in ((team, row["p"]), (opp, row["q"])):
                if side in points and points[side] != value:
                    score_conflict = True
                points.setdefault(side, value)
        if row.get("neutral_site"):
            neutral = True
        home_claims.add(opp if row.get("away") else team)
    if neutral:
        site = "NEUTRAL"
    elif len(home_claims) == 1:
        site = next(iter(home_claims))
    else:
        site = "UNKNOWN"
    return {"participants": participants, "points": points, "score_conflict": score_conflict, "site": site,
            "seasons": seasons, "dates": dates, "statuses": statuses, "observations": len(observations),
            "names": names, "obs": observations}


def producer_side_token(contest, side):
    ts = contest.get("%s_team_season_id" % side)
    return str(ts) if ts is not None else "EXT"


def stage_contest(ctx):
    seasons = delivery_seasons(ctx)
    verify = ctx.check("manifest_verification")
    info = verify_stage_manifest(ctx, ctx.manifest_path, "contest", verify, "stage")
    ctx.manifest_identity = info["identity"]
    m1 = verify_upstream(ctx, info, verify)
    _, contests = load_jsonl_output(info, "contests.jsonl.gz")
    _, orientations = load_jsonl_output(info, "orientations.jsonl.gz")
    _, reverse_rows = load_jsonl_output(info, "cfbd_reverse.jsonl.gz")
    _, schedule_rows = load_jsonl_output(info, "schedule_reconciliation.jsonl.gz")
    _, bindings = load_jsonl_output(m1, "identity_bindings.jsonl.gz")
    check_row_counts(ctx, info, {"contests": len(contests), "orientations": len(orientations),
                                 "schedule_reconciliation": len(schedule_rows)})

    inputs_check = ctx.check("manifest_inputs")
    declared = info["doc"].get("inputs") or {}
    bindings_contract = contract_section(ctx, "input_bindings")
    for key, expect in (("cfbd_fbs_route", bindings_contract.get("cfbd_fbs_route")),
                        ("cfbd_fcs_route", bindings_contract.get("cfbd_fcs_route")),
                        ("bat652_spine_membership", (bindings_contract.get("bat652_spine_membership") or {}).get(
                            "sha256"))):
        if declared.get(key) != expect:
            inputs_check.disagree({"field": "identity_document.inputs.%s" % key, "producer": declared.get(key),
                                   "contract": expect})
    manifests = load_bound_manifests(ctx, seasons, inputs_check)
    pages = load_pages(ctx, manifests)
    cfbd, route_conflicts = load_cfbd_union(ctx, inputs_check)
    inputs_check.counts["pages_parsed"] = sum(1 for p in pages.values() if p["parsed"] is not None)
    inputs_check.counts["rehash_failures"] = sum(1 for p in pages.values() if not p["rehash_ok"])

    ts_code = {}
    ts_season = {}
    ts_org = {}
    for (season, ts), page in pages.items():
        ts_season[ts] = season
        if page["parsed"] is not None:
            ts_org[ts] = page["parsed"]["org_id"]
            if page["parsed"]["decode_state"] == "DECODED":
                ts_code[ts] = page["parsed"]["code"]
    org_season_code = {}
    for ts, code in ts_code.items():
        org_season_code[(ts_org.get(ts), ts_season[ts])] = code

    independent, nolink = build_independent_contests(pages)
    by_key = {}
    duplicate_keys = []
    for contest in contests:
        key = contest.get("contest_key")
        if key in by_key:
            duplicate_keys.append(key)
        by_key[key] = contest

    # ---- check 1: contest reconstruction
    check = ctx.check("contest_reconstruction")
    for key in duplicate_keys:
        check.disagree({"problem": "DUPLICATE_CONTEST_KEY", "contest_key": key})
    counts = collections.Counter()
    for cid, mine in sorted(independent.items(), key=lambda item: int(item[0])):
        counts["independent_linked_contests"] += 1
        di = any(ts_code.get(p) in ("11", "12") for p in mine["participants"] if p != "EXT")
        if di:
            counts["independent_with_division_i_participant"] += 1
        if len(mine["participants"]) != 2:
            counts["independent_participant_anomalies"] += 1
        if mine["score_conflict"]:
            counts["independent_mirror_score_conflicts"] += 1
        if len(mine["seasons"]) != 1:
            counts["independent_multi_season"] += 1
        theirs = by_key.get("ncaa:%s" % cid)
        if theirs is None:
            if di:
                check.disagree({"contest_key": "ncaa:%s" % cid, "problem": "DIVISION_I_CONTEST_MISSING",
                                "participants": sorted(mine["participants"]),
                                "raw_sha256": [page["raw_sha256"] for page, _ in mine["obs"]]})
            continue
        counts["compared"] += 1
        problems = []
        theirs_participants = {producer_side_token(theirs, "a"), producer_side_token(theirs, "b")}
        if theirs_participants != mine["participants"]:
            problems.append(("participants", sorted(mine["participants"]), sorted(theirs_participants)))
        else:
            for side in ("a", "b"):
                token = producer_side_token(theirs, side)
                if not mine["score_conflict"] and mine["points"].get(token) != theirs.get("%s_points" % side):
                    problems.append(("%s_points" % side, mine["points"].get(token), theirs.get("%s_points" % side)))
                if token != "EXT" and theirs.get("%s_division_code" % side) != ts_code.get(token):
                    problems.append(("%s_division_code" % side, ts_code.get(token),
                                     theirs.get("%s_division_code" % side)))
            site = mine["site"]
            if site not in ("NEUTRAL", "UNKNOWN"):
                site = "HOME_A" if producer_side_token(theirs, "a") == site else "HOME_B"
            if theirs.get("site") != site:
                problems.append(("site", site, theirs.get("site")))
        status = "COMPLETED" if mine["statuses"] == {"COMPLETED"} else "/".join(sorted(str(s) for s in mine["statuses"]))
        if theirs.get("contest_status") != status:
            problems.append(("contest_status", status, theirs.get("contest_status")))
        if len(mine["seasons"]) == 1 and theirs.get("season") != next(iter(mine["seasons"])):
            problems.append(("season", next(iter(mine["seasons"])), theirs.get("season")))
        if theirs.get("contest_date") not in mine["dates"]:
            problems.append(("contest_date", sorted(d for d in mine["dates"] if d), theirs.get("contest_date")))
        if theirs.get("source") != "NCAA_GRAPH":
            problems.append(("source", "NCAA_GRAPH", theirs.get("source")))
        for field, value, producer in problems:
            check.disagree({"contest_key": "ncaa:%s" % cid, "field": field, "validator": value, "producer": producer,
                            "raw_sha256": [page["raw_sha256"] for page, _ in mine["obs"]]})
    for key, contest in by_key.items():
        if isinstance(key, str) and key.startswith("ncaa:"):
            counts["producer_ncaa_contests"] += 1
            if key[5:] not in independent:
                check.disagree({"contest_key": key, "problem": "PRODUCER_CONTEST_NOT_IN_RAW_PAGES"})
            if contest.get("ncaa_contest_id") != key[5:]:
                check.disagree({"contest_key": key, "field": "ncaa_contest_id", "producer": contest.get(
                    "ncaa_contest_id")})
    producer_nolink = {}
    for key, contest in by_key.items():
        if isinstance(key, str) and key.startswith("nolink:"):
            tokens = []
            for side in ("a", "b"):
                ts = contest.get("%s_team_season_id" % side)
                tokens.append(str(ts) if ts is not None else "EXT:" + name_key(contest.get("%s_team_name" % side)))
            producer_nolink[(contest.get("season"), contest.get("contest_date"), frozenset(tokens))] = contest
    for group_key, mine in sorted(nolink.items(), key=lambda item: (item[0][0], str(item[0][1]), sorted(item[0][2]))):
        di = any(ts_code.get(p) in ("11", "12") for p in group_key[2])
        if not di:
            continue
        counts["independent_nolink_with_division_i_participant"] += 1
        theirs = producer_nolink.get(group_key)
        if theirs is None:
            check.disagree({"problem": "DIVISION_I_NOLINK_CONTEST_MISSING", "season": group_key[0],
                            "date": group_key[1], "participants": sorted(group_key[2]),
                            "raw_sha256": [page["raw_sha256"] for page, _ in mine["obs"]]})
            continue
        counts["nolink_compared"] += 1
        status = next(iter(mine["statuses"])) if len(mine["statuses"]) == 1 else "/".join(
            sorted(str(s) for s in mine["statuses"]))
        if theirs.get("contest_status") != status:
            check.disagree({"contest_key": theirs.get("contest_key"), "field": "contest_status", "validator": status,
                            "producer": theirs.get("contest_status"),
                            "raw_sha256": [page["raw_sha256"] for page, _ in mine["obs"]]})
        if status == "COMPLETED" and not mine["score_conflict"]:
            for side in ("a", "b"):
                ts = theirs.get("%s_team_season_id" % side)
                token = str(ts) if ts is not None else "EXT"
                if mine["points"].get(token) != theirs.get("%s_points" % side):
                    check.disagree({"contest_key": theirs.get("contest_key"), "field": "%s_points" % side,
                                    "validator": mine["points"].get(token),
                                    "producer": theirs.get("%s_points" % side)})
    for group_key, contest in producer_nolink.items():
        if group_key not in nolink:
            check.disagree({"contest_key": contest.get("contest_key"), "problem": "PRODUCER_NOLINK_NOT_IN_RAW_PAGES"})
    check.counts.update(counter_dict(counts))
    check.counts["independent_nolink_contests"] = len(nolink)
    check.counts["producer_nolink_contests"] = len(producer_nolink)

    # ---- check 2: FCS-FCS
    check = ctx.check("fcs_fcs")
    graph_fcs = collections.Counter()
    for cid, mine in independent.items():
        parts = [p for p in mine["participants"] if p != "EXT"]
        if len(mine["participants"]) == 2 and len(parts) == 2 and all(ts_code.get(p) == "12" for p in parts):
            graph_fcs[ts_season[parts[0]]] += 1
    nolink_fcs = collections.Counter()
    for key, mine in nolink.items():
        parts = [p for p in mine["participants"] if not str(p).startswith("EXT")]
        if len(mine["participants"]) == 2 and len(parts) == 2 and all(ts_code.get(p) == "12" for p in parts):
            nolink_fcs[key[0]] += 1
    cfbd_to_org = collections.defaultdict(set)
    for row in bindings:
        if row.get("cfbd_team_id") is not None:
            cfbd_to_org[str(row["cfbd_team_id"])].add(str(row.get("org_id")))
    cfbd_fcs = collections.Counter()
    producer_fcs = collections.Counter()
    producer_graph_fcs = collections.Counter()
    for contest in contests:
        if contest.get("classification_pair") == "FCS-FCS":
            producer_fcs[contest.get("season")] += 1
            if contest.get("source") == "NCAA_GRAPH":
                producer_graph_fcs[contest.get("season")] += 1
        key = contest.get("contest_key")
        if isinstance(key, str) and key.startswith("cfbd:"):
            game = cfbd.get(key[5:])
            if game is None:
                continue
            orgs = []
            for team in (game["home"], game["away"]):
                bound_orgs = cfbd_to_org.get(team, set())
                orgs.append(next(iter(bound_orgs)) if len(bound_orgs) == 1 else None)
            if all(o is not None and org_season_code.get((o, game["season"])) == "12" for o in orgs):
                cfbd_fcs[game["season"]] += 1
    per_season = {}
    for season in seasons:
        mine_graph = graph_fcs[season] + nolink_fcs[season]
        mine_total = mine_graph + cfbd_fcs[season]
        per_season[str(season)] = {"validator_graph": mine_graph, "validator_cfbd_only": cfbd_fcs[season],
                                   "validator_total": mine_total, "producer_total": producer_fcs[season],
                                   "producer_graph": producer_graph_fcs[season]}
        if mine_total <= 0:
            check.disagree({"season": season, "problem": "NO_FCS_FCS_CONTESTS"})
        if mine_total != producer_fcs[season] or mine_graph != producer_graph_fcs[season]:
            check.disagree({"season": season, "validator_graph": mine_graph, "producer_graph":
                            producer_graph_fcs[season], "validator_total": mine_total,
                            "producer_total": producer_fcs[season]})
    check.counts["per_season"] = per_season

    # ---- check 3: orientation invariants
    check = ctx.check("orientation_invariants")
    sides = collections.defaultdict(dict)
    for row in orientations:
        key = row.get("contest_key")
        side = row.get("side")
        if side in sides[key]:
            check.disagree({"contest_key": key, "problem": "DUPLICATE_SIDE", "side": side})
        sides[key][side] = row
    complement = {"W": "L", "L": "W", "T": "T", None: None}
    for key, rows in sides.items():
        contest = by_key.get(key)
        if contest is None:
            check.disagree({"contest_key": key, "problem": "ORIENTATION_WITHOUT_CONTEST"})
            continue
        if set(rows) != {0, 1}:
            check.disagree({"contest_key": key, "problem": "SIDES", "sides": sorted(rows, key=str)})
            continue
        zero, one = rows[0], rows[1]
        problems = []
        if zero.get("team_points") != one.get("opponent_points") or zero.get("opponent_points") != one.get(
                "team_points"):
            problems.append("POINTS_DO_NOT_MIRROR")
        margins = (zero.get("margin"), one.get("margin"))
        if None in margins:
            if margins != (None, None):
                problems.append("MARGIN_PARTIAL")
        elif margins[0] + margins[1] != 0:
            problems.append("MARGINS_DO_NOT_SUM_TO_ZERO")
        for row in (zero, one):
            if row.get("team_points") is not None and row.get("opponent_points") is not None and row.get(
                    "margin") != row["team_points"] - row["opponent_points"]:
                problems.append("MARGIN_NOT_POINT_DIFFERENCE")
        if complement.get(zero.get("result"), "?") != one.get("result"):
            problems.append("RESULTS_DO_NOT_COMPLEMENT")
        for row in (zero, one):
            for field in ("classification_pair", "disposition", "reconciliation_state"):
                if row.get(field) != contest.get(field):
                    problems.append("%s_DIFFERS_FROM_CONTEST" % field.upper())
        for row, side in ((zero, "a"), (one, "b")):
            if row.get("team_season_id") != contest.get("%s_team_season_id" % side) or row.get(
                    "team_points") != contest.get("%s_points" % side):
                problems.append("SIDE_%s_NOT_CONTEST_%s" % (row.get("side"), side.upper()))
        for problem in sorted(set(problems)):
            check.disagree({"contest_key": key, "problem": problem})
    missing = [key for key in by_key if key not in sides]
    for key in missing:
        check.disagree({"contest_key": key, "problem": "CONTEST_WITHOUT_ORIENTATIONS"})
    check.counts.update(orientation_rows=len(orientations), contest_keys_with_orientations=len(sides),
                        contests=len(by_key))

    # ---- check 4: single-source seasons
    check = ctx.check("single_source_seasons")
    single = set(contract_section(ctx, "reconciliation", "single_source_seasons"))
    two = set(contract_section(ctx, "reconciliation", "two_source_seasons"))
    single_state = contract_section(ctx, "reconciliation", "single_source_state")
    exposure = contract_section(ctx, "reconciliation", "single_source_exposure")
    reconciled_state = contract_section(ctx, "reconciliation", "reconciled_state")
    counts = collections.Counter()
    for contest in contests:
        season = contest.get("season")
        key = contest.get("contest_key")
        if season in single:
            counts["single_source_contests"] += 1
            problems = []
            if contest.get("reconciliation_state") != single_state:
                problems.append(("reconciliation_state", contest.get("reconciliation_state")))
            if contest.get("exposure") != exposure:
                problems.append(("exposure", contest.get("exposure")))
            if contest.get("cfbd_game_ids"):
                problems.append(("cfbd_game_ids", contest.get("cfbd_game_ids")))
            if contest.get("disposition") == "VERIFIED_PRESENT":
                problems.append(("disposition", "VERIFIED_PRESENT"))
            for field, value in problems:
                check.disagree({"contest_key": key, "season": season, "field": field, "producer": value})
        if contest.get("reconciliation_state") == reconciled_state and season not in two:
            check.disagree({"contest_key": key, "season": season, "problem": "RECONCILED_OUTSIDE_2016_2023"})
        if season not in seasons:
            check.disagree({"contest_key": key, "season": season, "problem": "SEASON_OUTSIDE_SCOPE"})
    check.counts.update(counter_dict(counts))

    # ---- check 5: reconciled contests
    check = ctx.check("reconciled_contests")
    org_to_cfbd = collections.defaultdict(set)
    for row in bindings:
        if row.get("cfbd_team_id") is not None:
            org_to_cfbd[str(row.get("org_id"))].add(str(row["cfbd_team_id"]))
    references = collections.defaultdict(list)
    for contest in contests:
        for gid in contest.get("cfbd_game_ids") or []:
            references[str(gid)].append(contest.get("contest_key"))
    counts = collections.Counter()
    for contest in contests:
        key = contest.get("contest_key")
        if contest.get("disposition") == "VERIFIED_PRESENT" and (contest.get("reconciliation_state") != reconciled_state
                                                                  or contest.get("conflict_fields")):
            check.disagree({"contest_key": key, "problem": "VERIFIED_WITHOUT_CLEAN_RECONCILIATION",
                            "reconciliation_state": contest.get("reconciliation_state"),
                            "conflict_fields": contest.get("conflict_fields")})
        if contest.get("reconciliation_state") != reconciled_state:
            continue
        counts["reconciled"] += 1
        ids = [str(g) for g in contest.get("cfbd_game_ids") or []]
        if len(ids) != 1:
            check.disagree({"contest_key": key, "problem": "NOT_EXACTLY_ONE_CFBD_GAME", "cfbd_game_ids": ids})
            continue
        game = cfbd.get(ids[0])
        problems = []
        if game is None:
            check.disagree({"contest_key": key, "problem": "CFBD_GAME_NOT_IN_BOUND_ROUTES", "cfbd_game_id": ids[0]})
            continue
        if game["season"] != contest.get("season"):
            problems.append(("season", game["season"], contest.get("season")))
        start = utc_date(game["start"])
        try:
            contest_date = datetime.date.fromisoformat(str(contest.get("contest_date")))
        except ValueError:
            contest_date = None
        if start is None or contest_date is None or abs((start - contest_date).days) > 1:
            problems.append(("contest_date_vs_cfbd_startDate_utc", str(start), contest.get("contest_date")))
        a_team, b_team = str(contest.get("a_cfbd_team_id")), str(contest.get("b_cfbd_team_id"))
        if {a_team, b_team} != {game["home"], game["away"]} or a_team == b_team:
            problems.append(("cfbd_team_ids", sorted([game["home"], game["away"]]), sorted([a_team, b_team])))
        else:
            points = {game["home"]: game["home_points"], game["away"]: game["away_points"]}
            if (points[a_team], points[b_team]) != (contest.get("a_points"), contest.get("b_points")):
                problems.append(("oriented_score", [points[a_team], points[b_team]],
                                 [contest.get("a_points"), contest.get("b_points")]))
        if len(references[ids[0]]) != 1:
            problems.append(("cfbd_game_referenced_by", [key], references[ids[0]]))
        for side in ("a", "b"):
            org = contest.get("%s_org_id" % side)
            team = str(contest.get("%s_cfbd_team_id" % side))
            if org is None or org_to_cfbd.get(str(org)) != {team}:
                problems.append(("%s_identity_binding" % side, sorted(org_to_cfbd.get(str(org), set())), team))
        for field, mine, theirs in problems:
            check.disagree({"contest_key": key, "cfbd_game_id": ids[0], "field": field, "validator_cfbd": mine,
                            "producer": theirs})
    check.counts.update(counter_dict(counts))

    # ---- check 6: reverse join
    check = ctx.check("cfbd_reverse_join")
    reverse = collections.defaultdict(list)
    for row in reverse_rows:
        reverse[str(row.get("cfbd_game_id"))].append(row)
    counts = collections.Counter()
    not_one_to_one = collections.Counter()
    observed = []
    for gid, game in sorted(cfbd.items()):
        if game["home_class"] not in ("fbs", "fcs") and game["away_class"] not in ("fbs", "fcs"):
            counts["games_without_fbs_fcs_participant"] += 1
            continue
        counts["games_with_fbs_fcs_participant"] += 1
        refs = references.get(gid, [])
        if len(refs) == 0:
            counts["unmatched"] += 1
            check.disagree({"cfbd_game_id": gid, "season": game["season"], "problem": "UNMATCHED",
                            "reverse_rows": reverse.get(gid, [])[:2]})
            continue
        if len(refs) > 1:
            # Accepted only when every referencing contest is CONFLICT and its own row marks NOT_ONE_TO_ONE.
            counts["multiply_matched"] += 1
            referencing = [by_key.get(ref) or {} for ref in refs]
            explicit = len(set(refs)) == len(refs) and all(
                contest.get("disposition") == "CONFLICT" and marks_not_one_to_one(contest) for contest in referencing)
            if not explicit:
                check.disagree({"cfbd_game_id": gid, "season": game["season"], "problem": "MULTIPLY_MATCHED",
                                "contest_keys": refs,
                                "contest_markers": [[contest.get("disposition"), contest.get("disposition_reason"),
                                                     contest.get("flags"), contest.get("conflict_fields")]
                                                    for contest in referencing]})
                continue
            counts["multiply_matched_explicit_not_one_to_one"] += 1
            not_one_to_one[game["season"]] += 1
            observed.append({"cfbd_game_id": gid, "season": game["season"], "contest_keys": sorted(refs)})
            rows = reverse.get(gid, [])
            row_ok = sorted(str(row.get("contest_key")) for row in rows) == sorted(refs) and all(
                row.get("disposition") == (by_key.get(row.get("contest_key")) or {}).get("disposition")
                and row.get("reconciliation_state") == (by_key.get(row.get("contest_key")) or {}).get(
                    "reconciliation_state") for row in rows)
            if not row_ok:
                check.disagree({"cfbd_game_id": gid, "problem": "REVERSE_ROWS_DISAGREE_WITH_NOT_ONE_TO_ONE_CONTESTS",
                                "contest_keys": refs, "reverse_rows": rows[:4]})
            continue
        rows = reverse.get(gid, [])
        contest = by_key.get(refs[0]) or {}
        if len(rows) != 1 or rows[0].get("contest_key") != refs[0] or rows[0].get("disposition") != contest.get(
                "disposition") or rows[0].get("reconciliation_state") != contest.get("reconciliation_state"):
            check.disagree({"cfbd_game_id": gid, "problem": "REVERSE_ROW_DISAGREES", "contest_key": refs[0],
                            "reverse_rows": rows[:2]})
    for gid in references:
        if gid not in cfbd:
            check.disagree({"cfbd_game_id": gid, "problem": "REFERENCED_GAME_NOT_IN_BOUND_ROUTES",
                            "contest_keys": references[gid]})
    for conflict in route_conflicts:
        counts["route_conflicts"] += 1
    check.counts.update(counter_dict(counts))
    check.counts["reverse_rows"] = len(reverse_rows)
    check.counts["explicit_not_one_to_one_games_by_season"] = {
        str(season): not_one_to_one[season] for season in contract_section(ctx, "reconciliation", "two_source_seasons")}
    check.counts["explicit_not_one_to_one_games_head"] = observed[:HEAD_LIMIT]

    # ---- check 7: schedule cardinality
    check = ctx.check("schedule_cardinality")
    involving = collections.Counter()
    for contest in contests:
        if contest.get("source") != "NCAA_GRAPH":
            continue
        for ts in {contest.get("a_team_season_id"), contest.get("b_team_season_id")} - {None}:
            involving[str(ts)] += 1
    states = {}
    for row in schedule_rows:
        states[str(row.get("ncaa_team_season_id"))] = row
    counts = collections.Counter()
    explicit_cells = []
    for (season, ts), page in sorted(pages.items()):
        parsed = page["parsed"]
        if parsed is None or parsed["decode_state"] != "DECODED" or parsed["code"] not in ("11", "12"):
            continue
        counts["division_i_pages"] += 1
        rows = parsed["rows"]
        completed = [r for r in rows if r.get("status") == "COMPLETED" and not r.get("exempt")]
        header = parsed["header"]
        header_wlt = None if header is None else (header["wins"], header["losses"], header["ties"] or 0)
        by_letter = wlt(collections.Counter(r.get("letter") for r in completed))
        by_score = wlt(collections.Counter("W" if r["p"] > r["q"] else "L" if r["p"] < r["q"] else "T"
                                           for r in completed))
        # Every schedule-vs-header mismatch visible in the raw page; each must be an explicit producer row.
        kinds = []
        if len(rows) != involving.get(ts, 0):
            kinds.append("ROW_COUNT")
        if header_wlt is None:
            kinds.append("HEADER_ABSENT")
        else:
            if sum(header_wlt) != len(completed):
                kinds.append("HEADER_SUM")
            if header_wlt != by_letter:
                kinds.append("HEADER_VS_RESULT_LETTERS")
            if header_wlt != by_score:
                kinds.append("HEADER_VS_SCORES")
        produced = states.get(ts)
        state = produced.get("state") if produced else None
        evidence = {"season": season, "team_season_id": ts, "org_id": parsed["org_id"],
                    "raw_sha256": page["raw_sha256"], "mismatch_kinds": kinds, "page_rows": len(rows),
                    "producer_graph_contests": involving.get(ts, 0), "header_wlt": header_wlt,
                    "result_letters_wlt": by_letter, "scores_wlt": by_score, "producer_state": state}
        if produced is None:
            check.disagree(dict(evidence, problem="NO_EXPLICIT_PRODUCER_RECONCILIATION_ROW"))
            continue
        if kinds:
            counts["raw_mismatch_pages"] += 1
            for kind in kinds:
                counts["raw_mismatch_kind_%s" % kind] += 1
            header_named = any(word in str(state) for word in ("HEADER", "RECORD"))
            row_named = any(word in str(state) for word in ("ROW", "CONTEST", "CARDINALITY"))
            named = state not in (None, "MATCH") and (
                ("ROW_COUNT" in kinds and row_named) or (any(k != "ROW_COUNT" for k in kinds) and header_named))
            if named:
                counts["raw_mismatches_surfaced_as_explicit_rows"] += 1
                explicit_cells.append({"cell_key": produced.get("cell_key"), "state": state, "kinds": kinds,
                                       "header_wlt": header_wlt, "result_letters_wlt": by_letter,
                                       "scores_wlt": by_score})
            else:
                check.disagree(dict(evidence, problem="RAW_MISMATCH_NOT_SURFACED_AS_EXPLICIT_ROW"))
        elif state != "MATCH":
            check.disagree(dict(evidence, problem="PRODUCER_MISMATCH_ROW_WITHOUT_RAW_MISMATCH"))
        for field, mine in (("page_rows", len(rows)), ("ncaa_org_id", parsed["org_id"]), ("season", season)):
            if produced.get(field) != mine:
                check.disagree({"season": season, "team_season_id": ts, "field": field, "validator": mine,
                                "producer": produced.get(field)})
        record = produced.get("header_record")
        theirs = None if not isinstance(record, dict) else (record.get("wins"), record.get("losses"),
                                                           record.get("ties") or 0)
        if theirs != header_wlt:
            check.disagree({"season": season, "team_season_id": ts, "field": "header_record",
                            "validator": header_wlt, "producer": record})
        derived = produced.get("derived_record")
        derived_wlt = None if not isinstance(derived, dict) else (derived.get("wins"), derived.get("losses"),
                                                                  derived.get("ties") or 0)
        if derived_wlt not in (by_letter, by_score):
            check.disagree({"season": season, "team_season_id": ts, "field": "derived_record",
                            "validator_letters": by_letter, "validator_scores": by_score, "producer": derived})
    check.counts.update(counter_dict(counts))
    check.counts["explicit_mismatch_cells"] = explicit_cells[:HEAD_LIMIT]
    check.counts["producer_rows"] = len(schedule_rows)
    check.counts["producer_states"] = counter_dict(collections.Counter(row.get("state") for row in schedule_rows))
    if len(schedule_rows) != counts["division_i_pages"]:
        check.disagree({"problem": "RECONCILIATION_ROW_COUNT", "producer_rows": len(schedule_rows),
                        "division_i_pages": counts["division_i_pages"]})


# ----------------------------------------------------------------------------------------- stage: subsets


def stage_subsets(ctx):
    verify = ctx.check("manifest_verification")
    info = verify_stage_manifest(ctx, ctx.manifest_path, "contest", verify, "stage")
    ctx.manifest_identity = info["identity"]
    verify_upstream(ctx, info, verify)
    _, contests = load_jsonl_output(info, "contests.jsonl.gz")
    subsets = load_json_output(info, "subsets.json")
    check = ctx.check("subsets")
    if not isinstance(subsets, dict):
        raise Refusal("OUTPUT_MALFORMED", "subsets.json is not an object")
    parent = {}
    for contest in contests:
        key = contest.get("contest_key")
        if key in parent:
            check.disagree({"problem": "DUPLICATE_PARENT_KEY", "contest_key": key})
        parent[key] = contest
    rules = {
        "FBS_ESTIMAND_SUBSET": lambda c: c.get("a_division_code") == "11" and c.get("b_division_code") == "11",
        "FCS_SUBSET": lambda c: c.get("a_division_code") == "12" or c.get("b_division_code") == "12",
    }
    for name, rule in rules.items():
        keys = subsets.get(name)
        if not isinstance(keys, list):
            check.disagree({"subset": name, "problem": "MISSING_OR_NOT_A_LIST"})
            continue
        counter = collections.Counter(keys)
        duplicates = [key for key, n in counter.items() if n > 1]
        for key in duplicates:
            check.disagree({"subset": name, "problem": "DUPLICATE", "contest_key": key})
        not_in_parent = [key for key in counter if key not in parent]
        for key in not_in_parent:
            check.disagree({"subset": name, "problem": "NOT_IN_PARENT", "contest_key": key})
        rule_failures = [key for key in counter if key in parent and not rule(parent[key])]
        for key in rule_failures:
            check.disagree({"subset": name, "problem": "RULE_NOT_SATISFIED", "contest_key": key,
                            "a_division_code": parent[key].get("a_division_code"),
                            "b_division_code": parent[key].get("b_division_code")})
        expected = {key for key, contest in parent.items() if rule(contest)}
        omitted = sorted(expected - set(counter), key=str)
        for key in omitted:
            check.disagree({"subset": name, "problem": "PARENT_ROW_OMITTED", "contest_key": key})
        check.counts[name] = {"rows": len(keys), "distinct": len(counter), "parent_rows_satisfying_rule": len(expected),
                              "duplicates": len(duplicates), "not_in_parent": len(not_in_parent),
                              "rule_failures": len(rule_failures), "omitted": len(omitted),
                              "by_season": counter_dict(collections.Counter(parent[k].get("season") for k in counter
                                                                            if k in parent))}
        proof = (subsets.get("proof") or {}).get(name) if isinstance(subsets.get("proof"), dict) else None
        if isinstance(proof, dict):
            mine = {"rows": len(keys), "distinct": len(counter),
                    "subset_of_parent": not not_in_parent}
            theirs = {k: proof.get(k) for k in mine}
            if mine != theirs:
                check.disagree({"subset": name, "problem": "PROOF_FIELDS", "validator": mine, "producer": theirs})
    check.counts["parent_rows"] = len(contests)


# ------------------------------------------------------------------------------------------------- driver


def build_parser():
    parser = argparse.ArgumentParser(
        description="Independent validator for the BAT-710 national Division I population 2016-2025.",
        allow_abbrev=False)
    parser.add_argument("--stage", required=True, choices=STAGES)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--report", required=True)
    parser.add_argument("--repo-root")
    return parser


def load_contract(ctx):
    if not ctx.contract_path.is_file():
        raise Refusal("CONTRACT_MISSING", "contract %s does not exist" % ctx.contract_path)
    raw = ctx.contract_path.read_bytes()
    ctx.contract_sha256 = sha256_bytes(raw)
    try:
        contract = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refusal("CONTRACT_MALFORMED", "contract is not JSON (%s)" % exc)
    if not isinstance(contract, dict):
        raise Refusal("CONTRACT_MALFORMED", "contract is not an object")
    ctx.contract = contract
    for path in (("input_bindings", "bound_manifests"), ("division_decoding", "table"),
                 ("reconciliation", "two_source_seasons"), ("program_season_dispositions",)):
        contract_section(ctx, *path)


def run(ctx):
    load_contract(ctx)
    if not ctx.data_root.is_dir():
        raise Refusal("DATA_ROOT_MISSING", "data root %s is not a directory" % ctx.data_root)
    if ctx.stage != "inputs" and ctx.manifest_path is None:
        raise Refusal("MANIFEST_MISSING", "stage %s requires --manifest" % ctx.stage)
    if ctx.stage == "inputs":
        stage_inputs(ctx)
    elif ctx.stage == "program-season":
        stage_program_season(ctx)
    elif ctx.stage == "contest":
        stage_contest(ctx)
    else:
        stage_subsets(ctx)


def main(argv=None):
    args = build_parser().parse_args(argv)
    started = time.monotonic()
    ctx = Context(args)
    report_path = pathlib.Path(args.report)
    if report_path.exists():
        print("refused: report %s already exists (reports are create-only)" % report_path, file=sys.stderr)
        return 2
    if not report_path.parent.is_dir():
        print("refused: report directory %s does not exist" % report_path.parent, file=sys.stderr)
        return 2
    refusal = None
    try:
        run(ctx)
    except Refusal as exc:
        refusal = exc.code
        check = ctx.check("manifest_verification" if exc.code.startswith(("MANIFEST", "OUTPUT", "CONTRACT_IDENTITY",
                                                                           "UPSTREAM")) else "refusal")
        check.disagree({"refusal": exc.code, "detail": exc.detail})
        print("REFUSED %s: %s" % (exc.code, exc.detail), file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - an internal error must never look like PASS or FAIL
        refusal = "VALIDATOR_INTERNAL_ERROR"
        lines = []
        trace = exc.__traceback__
        while trace is not None:
            lines.append(trace.tb_lineno)
            trace = trace.tb_next
        ctx.check("refusal").disagree({"refusal": refusal, "detail": "%s: %s" % (type(exc).__name__, exc),
                                       "lines": lines})
        print("REFUSED %s: %s: %s (lines %s)" % (refusal, type(exc).__name__, exc, lines), file=sys.stderr)
    checks = {name: check.to_json() for name, check in ctx.checks.items()}
    if refusal is not None:
        result = "REFUSED"
    elif any(check["result"] == "FAIL" for check in checks.values()):
        result = "FAIL"
    else:
        result = "PASS"
    report = {
        "label": REPORT_LABEL,
        "cycle_number": CYCLE_NUMBER,
        "attempt_number": ATTEMPT_NUMBER,
        "stage": args.stage,
        "contract_path": args.contract,
        "contract_sha256": ctx.contract_sha256,
        "manifest": args.manifest,
        "manifest_identity": ctx.manifest_identity,
        "result": result,
        "refusal": refusal,
        "checks": checks,
        "independence": {"imports": own_imports()},
        "seconds": round(time.monotonic() - started, 3),
    }
    with open(report_path, "x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    for name, check in checks.items():
        print("%-28s %s (%d disagreements)" % (name, check["result"], check["disagreement_count"]))
    print("result %s%s -> %s" % (result, " (%s)" % refusal if refusal else "", report_path))
    return {"PASS": 0, "FAIL": 1}.get(result, 2)


if __name__ == "__main__":
    sys.exit(main())
