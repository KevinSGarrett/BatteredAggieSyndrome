#!/usr/bin/env python3
"""Independent validator for the BAT-710 national Division I population 2016-2025 (Cycle #38 Attempt #1).

Contract V1.3 (V1.2 rules; route conflicts on parameters.cfbd_game_fact_fields only, metadata-only route
differences reported, CFBD match dates on every one-to-one match).  Every checked fact is reconstructed from raw
lake bytes and the contract (including its ``parameters`` block).  The validator uses the Python standard library only, imports no repository module and
never reads producer source (AGENTS rule 9).  Lake files are opened read-only; the only write is the
create-only ``--report`` file.

Stages (exit 0 = every check PASS, 1 = any check FAIL, 2 = REFUSED):

  inputs          L02 INPUT_BINDING: binding rule, capture rehash, CFBD routes, bound file hashes.
  program-season  L07 VALIDATE_M1: raw page decode, census, expected keys, dispositions, decoding proof,
                  identity-binding fingerprints, totals, transitions.
  contest         L09 VALIDATE_M2: contest reconstruction, forward matching on CFBD local dates, CFBD-only
                  rows, FCS-FCS, orientations, reconciliation, reverse join, cardinality.
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
THRESHOLD_KEYS = ("name_confirmed_min_games", "name_confirmed_min_share", "collision_other_max_share",
                  "fingerprint_only_min_games", "fingerprint_only_min_share", "fingerprint_only_runner_up_max_share")

DIVISION_I = "DIVISION_I"
OUTSIDE = "OUTSIDE_DIVISION_I"
NON_NCAA = "NON_NCAA"
UNRESOLVED = "UNRESOLVED"
EXTERNAL_MEMBERSHIPS = (OUTSIDE, NON_NCAA)
COMPLETED = "COMPLETED"
MIRROR = "MIRROR_DISAGREEMENT"
NOT_OBSERVED = "NOT_OFFICIALLY_OBSERVED"

# Expectations stated by the validator specification (VALIDATOR_SPEC_C38A01.md); deviations are FAIL.
SPEC_EXPECTED_FAILURES = {2016: 4, 2017: 4}
SPEC_EXPECTED_UNREFERENCED_SRC015 = 64
SPEC_EXPECTED_CODE_TALLIES = {
    2016: {"11": 127, "12": 124, "2": 171, "3": 234, "none": 3},
    2019: {"11": 130, "12": 126, "2": 167, "3": 237, "none": 0},
}
SPEC_EXPECTED_DECODING_PROOF = {"total": 562, "FBS": 380, "FCS": 163, "D-II": 19}

RE_TAG = re.compile(r"<[^>]+>")
RE_HISTORY_LINK = re.compile(r'href="/teams/history/MFB/(\d+)"')
RE_YEAR_SELECT = re.compile(r'<select\b[^>]*\bid="year_list"[^>]*>(.*?)</select>', re.S)
RE_OPTION = re.compile(r"<option\b([^>]*)>(.*?)</option>", re.S)
RE_VALUE_ATTR = re.compile(r'\bvalue="([^"]*)"')
RE_SELECTED_ATTR = re.compile(r"\bselected\b")
RE_RANKING_HREF = re.compile(r'href="(/rankings/[^"]*)"')
RE_QUERY_PARAM = re.compile(r"[?&]([^=&#]+)=([^&#]*)")
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
RE_MARKER_SPLIT = re.compile(r"[^A-Z0-9_]+")
RE_HEX64 = re.compile(r"^[0-9a-f]{64}$")


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
        self.params = None
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


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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


def utc_date(value):
    instant = parse_instant(value)
    return None if instant is None else instant.astimezone(datetime.timezone.utc).date()


def candidate_local_dates(start, offsets):
    """cfbd_date_basis: the calendar dates of the UTC instant shifted by each configured offset."""
    instant = parse_instant(start)
    if instant is None:
        return ()
    utc = instant.astimezone(datetime.timezone.utc)
    return tuple(sorted({(utc + datetime.timedelta(hours=hours)).date() for hours in offsets}))


def within_days(candidates, dates, days):
    return any(abs((candidate - date).days) <= days for candidate in candidates for date in dates)


def iso_date(value):
    try:
        return datetime.date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def text_of(fragment):
    return " ".join(html.unescape(RE_TAG.sub(" ", fragment)).split())


def name_key(name):
    return " ".join((name or "").lower().split())


def counter_dict(counter):
    return {str(key): counter[key] for key in sorted(counter, key=str)}


def has_marker(value, marker):
    """True when ``marker`` is a whole token of a string, or of any string nested in a list/dict."""
    if isinstance(value, str):
        return marker in RE_MARKER_SPLIT.split(value.upper())
    if isinstance(value, dict):
        return any(has_marker(k, marker) or has_marker(v, marker) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(has_marker(item, marker) for item in value)
    return False


def contest_marks(contest, marker):
    """Read a contest row's own reconciliation markers (disposition_reason, flags, conflict_fields)."""
    return any(has_marker(contest.get(field), marker) for field in ("disposition_reason", "flags", "conflict_fields"))


def conflict_field_names(contest):
    names = set()
    for item in contest.get("conflict_fields") or []:
        if isinstance(item, dict) and isinstance(item.get("field"), str):
            names.add(item["field"])
        elif isinstance(item, str):
            names.add(item)
    return names


def wlt(counter):
    return (counter.get("W", 0), counter.get("L", 0), counter.get("T", 0))


def delivery_seasons(ctx):
    seasons = ctx.contract.get("delivery_seasons")
    if not isinstance(seasons, list) or not seasons or not all(is_int(s) for s in seasons):
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


# -------------------------------------------------------------------------------------------- parameters


def load_parameters(ctx):
    """Validate contract['parameters'] (V1.2); refuse CONTRACT_PARAMETERS_INVALID when missing or malformed."""
    contract = ctx.contract
    params = contract.get("parameters")
    if not isinstance(params, dict):
        raise Refusal("CONTRACT_PARAMETERS_INVALID", "contract['parameters'] is missing or not an object")
    problems = []
    decoding = contract.get("division_decoding") if isinstance(contract.get("division_decoding"), dict) else {}
    table = decoding.get("table") if isinstance(decoding.get("table"), dict) else {}
    cross = (decoding.get("official_cross_check") or {}).get("labels") if isinstance(
        decoding.get("official_cross_check"), dict) else None
    days = params.get("forward_match_days")
    if not (is_int(days) and days >= 0):
        problems.append("forward_match_days must be a non-negative integer")
    offsets = params.get("cfbd_local_offset_hours")
    if not (isinstance(offsets, list) and offsets and all(is_int(h) and -24 < h < 24 for h in offsets)
            and len(set(offsets)) == len(offsets)):
        problems.append("cfbd_local_offset_hours must be a non-empty list of distinct integer hours")
    window = params.get("same_pair_same_score_window_days")
    if not (is_int(window) and window >= 0):
        problems.append("same_pair_same_score_window_days must be a non-negative integer")
    spring = iso_date(params.get("spring_2020_from"))
    if spring is None:
        problems.append("spring_2020_from must be an ISO date")
    thresholds = params.get("binding_thresholds")
    if not isinstance(thresholds, dict) or any(not is_number(thresholds.get(k)) or thresholds.get(k) < 0
                                               for k in THRESHOLD_KEYS):
        problems.append("binding_thresholds must hold non-negative numbers %s" % (THRESHOLD_KEYS,))
    elif any(thresholds[k] > 1 for k in THRESHOLD_KEYS if k.endswith("share")):
        problems.append("binding_thresholds shares must be <= 1")
    label_map = params.get("team_history_label_map")
    if not (isinstance(label_map, dict) and label_map and all(
            isinstance(k, str) and k and isinstance(v, str) and v for k, v in label_map.items())):
        problems.append("team_history_label_map must map non-empty strings to non-empty strings")
    label_codes = params.get("team_history_label_codes")
    if not (isinstance(label_codes, dict) and label_codes and all(
            isinstance(k, str) and v in table for k, v in label_codes.items())):
        problems.append("team_history_label_codes must map labels to codes of the decoding table")
    elif label_codes != cross:
        problems.append("team_history_label_codes differs from division_decoding.official_cross_check.labels")
    elif isinstance(label_map, dict) and not set(label_codes) <= set(label_map):
        problems.append("team_history_label_codes names a label absent from team_history_label_map")
    offset = params.get("ranking_link_academic_year_offset")
    if not is_int(offset):
        problems.append("ranking_link_academic_year_offset must be an integer")
    vocabulary = params.get("contest_status_vocabulary")
    grain = contract.get("contest_grain") if isinstance(contract.get("contest_grain"), dict) else {}
    if not (isinstance(vocabulary, list) and vocabulary and all(isinstance(s, str) and s for s in vocabulary)
            and len(set(vocabulary)) == len(vocabulary)):
        problems.append("contest_status_vocabulary must be a list of distinct strings")
    elif vocabulary != grain.get("contest_status_vocabulary"):
        problems.append("contest_status_vocabulary differs from contest_grain.contest_status_vocabulary")
    exposure = params.get("single_source_exposure")
    reconciliation = contract.get("reconciliation") if isinstance(contract.get("reconciliation"), dict) else {}
    if not (isinstance(exposure, str) and exposure):
        problems.append("single_source_exposure must be a non-empty string")
    elif exposure != reconciliation.get("single_source_exposure"):
        problems.append("single_source_exposure differs from reconciliation.single_source_exposure")
    fact_fields = params.get("cfbd_game_fact_fields")
    if not (isinstance(fact_fields, list) and fact_fields and all(isinstance(f, str) and f for f in fact_fields)
            and len(set(fact_fields)) == len(fact_fields) and "id" in fact_fields):
        problems.append("cfbd_game_fact_fields must be a list of distinct non-empty field names including 'id'")
    if problems:
        raise Refusal("CONTRACT_PARAMETERS_INVALID", "; ".join(problems))
    inferred = {}
    for code, entry in table.items():
        if isinstance(entry, dict) and isinstance(entry.get("inferred_meaning"), str):
            inferred[entry["inferred_meaning"]] = code
    ctx.params = {"forward_match_days": days, "offsets": list(offsets), "window_days": window, "spring": spring,
                  "thresholds": dict(thresholds), "label_map": dict(label_map), "label_codes": dict(label_codes),
                  "inferred_label_codes": inferred, "ranking_offset": offset, "vocabulary": list(vocabulary),
                  "exposure": exposure, "fact_fields": list(fact_fields), "raw": params}


def official_label_code(ctx, raw_label):
    """The page code an official label names: proving labels from the parameters, D-III via the inferred meaning."""
    if raw_label in ctx.params["label_codes"]:
        return ctx.params["label_codes"][raw_label]
    return ctx.params["inferred_label_codes"].get(raw_label)


def code_is_division_i(ctx, code):
    entry = contract_section(ctx, "division_decoding", "table").get(code)
    return bool(entry.get("division_i")) if isinstance(entry, dict) else None


def page_code_label(ctx, code):
    table = contract_section(ctx, "division_decoding", "table")
    entry = table.get(code) if code is not None else None
    return entry.get("label") if isinstance(entry, dict) else None


# ------------------------------------------------------------------------------------------ raw parsers


def decode_division(raw_codes):
    """Return (decode_state, canonical code or None) from the page's own counted division values."""
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
    """Status from the result cell; forfeit text is checked on the whole cell before any score (V1.2)."""
    row = {"contest_id": None, "result_text": None, "status": None, "letter": None, "p": None, "q": None,
           "ot": None, "exempt": False, "flags": []}
    whole = text_of(cell)
    link = RE_CONTEST_LINK.search(cell)
    if link:
        row["contest_id"] = link.group(1)
        text = text_of(link.group(2))
        row["exempt"] = "*" in text_of(link.group(3))
    else:
        text = whole
    row["result_text"] = text
    score = RE_SCORE.match(text)
    lowered = whole.lower()
    if score:
        letter, p, q = score.group(1), int(score.group(2)), int(score.group(3))
        row.update(letter=letter, p=p, q=q)
        if score.group(4) is not None:
            row["ot"] = int(score.group(4))
            if row["ot"] < 0:
                row["flags"].append("NEGATIVE_OVERTIME_MARKER")
        if (letter == "W" and not p > q) or (letter == "L" and not p < q) or (letter == "T" and p != q):
            row["flags"].append("RESULT_LETTER_CONTRADICTS_SCORE")
    if "forfeit" in lowered:
        row["status"] = "FORFEIT"
    elif score:
        row["status"] = COMPLETED
    elif lowered in ("canceled", "cancelled"):
        row["status"] = "CANCELED"
    elif lowered == "ppd":
        row["status"] = "UNSCORED"
    elif "no contest" in lowered:
        row["status"] = "NO_CONTEST"
    else:
        row["status"] = "UNPARSED"
        row["flags"].append("UNPARSED_RESULT")
    if row["exempt"]:
        row["flags"].append("EXEMPTED_NOT_COUNTED")
    return row


def parse_team_season_page(text, season, ranking_offset):
    page = {"flags": []}
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
    # division_decoding.source_field (V1.2): only ranking links whose org_id is the page organization and whose
    # academic_year is season + offset (N or N.0) count; any other division-bearing ranking link is flagged.
    org = page["org_id"]
    years = {str(season + ranking_offset), "%d.0" % (season + ranking_offset)}
    counted = []
    every = []
    mismatched = 0
    for href in RE_RANKING_HREF.finditer(text):
        query = RE_QUERY_PARAM.findall(html.unescape(href.group(1)))
        divisions = [v for k, v in query if k == "division"]
        if not divisions:
            continue
        every.extend(divisions)
        orgs_q = [v for k, v in query if k == "org_id"]
        years_q = [v for k, v in query if k == "academic_year"]
        if org is not None and orgs_q and all(v == org for v in orgs_q) and years_q and all(v in years for v in years_q):
            counted.extend(divisions)
        else:
            mismatched += 1
    page["ranking_link_mismatches"] = mismatched
    if mismatched:
        page["flags"].append("RANKING_LINK_IDENTITY_MISMATCH")
    page["raw_codes"] = sorted(set(counted))
    page["all_ranking_link_codes"] = sorted(set(every))
    page["decode_state"], page["code"] = decode_division(counted)
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


def accounting_problems(doc):
    """manifest_binding_rule.discovered_ids_accounted: every discovered id is a capture or failure; no id twice."""
    captures = [str(c.get("team_season_id")) for c in doc.get("captures") or []]
    failures = [str(f.get("team_season_id")) for f in doc.get("failures") or []]
    discovered = [str(x) for x in doc.get("discovered_team_season_ids") or []]
    problems = []
    duplicate = sorted(ts for ts, n in collections.Counter(captures).items() if n > 1)
    if duplicate:
        problems.append(("DUPLICATE_CAPTURE_IN_BOUND_MANIFEST", duplicate[:20]))
    unaccounted = sorted(set(discovered) - set(captures) - set(failures))
    if unaccounted:
        problems.append(("DISCOVERED_ID_NOT_ACCOUNTED", unaccounted[:20]))
    extra = sorted((set(captures) | set(failures)) - set(discovered))
    if extra or set(captures) & set(failures):
        problems.append(("CAPTURE_OR_FAILURE_NOT_DISCOVERED_OR_BOTH", sorted(extra)[:20]))
    return problems


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
        for code, sample in accounting_problems(doc):
            raise Refusal(code if code != "CAPTURE_OR_FAILURE_NOT_DISCOVERED_OR_BOTH" else "DISCOVERED_ID_NOT_ACCOUNTED",
                          "bound manifest %d: %s %s" % (season, code, sample))
        result[season] = {"identity": expect.get("identity"), "sha256": digest, "doc": doc}
    check.counts["bound_manifests"] = {
        str(season): {"identity": info["identity"], "captures": len(info["doc"].get("captures") or []),
                      "failures": len(info["doc"].get("failures") or [])}
        for season, info in sorted(result.items())
    }
    return result


def read_page(ctx, relative, declared, season):
    record = {"exists": False, "rehash_ok": False, "name_ok": False, "parsed": None}
    path = data_path(ctx, relative or "")
    if relative and path.is_file():
        record["exists"] = True
        data = path.read_bytes()
        record["rehash_ok"] = sha256_bytes(data) == declared
        record["name_ok"] = path.name == "%s.html" % declared
        if record["rehash_ok"]:
            record["parsed"] = parse_team_season_page(data.decode("utf-8", errors="replace"), season,
                                                      ctx.params["ranking_offset"])
    return record


def load_pages(ctx, manifests):
    """Read every bound capture once: rehash and parse.  Returns {(season, team_season_id): page}."""
    pages = {}
    for season, info in sorted(manifests.items()):
        for capture in info["doc"].get("captures") or []:
            ts = str(capture.get("team_season_id"))
            relative = capture.get("raw_relative_path") or ""
            declared = capture.get("raw_sha256")
            record = {"season": season, "ts": ts, "raw_relative_path": relative, "raw_sha256": declared}
            record.update(read_page(ctx, relative, declared, season))
            parsed = record["parsed"]
            record["identity_ok"] = parsed is not None and parsed["selected"] == (season_label(season), ts)
            pages[(season, ts)] = record
    return pages


def superseded_census(ctx, season, entries, bound_identity):
    """manifest_binding_rule.superseded_census / superseded_pair_absent_from_bound, independently."""
    bound_entry = next((e for e in entries if e["dir"] == bound_identity), None)
    if bound_entry is None or bound_entry["doc"] is None:
        raise Refusal("INPUT_BINDING_MISMATCH", "season %d bound manifest %s not found" % (season, bound_identity))
    bound_caps = bound_entry["doc"].get("captures") or []
    bound_pairs = {(str(c.get("team_season_id")), c.get("raw_sha256")) for c in bound_caps}
    bound_files = {str(c.get("raw_relative_path") or "").replace("\\", "/").rsplit("/", 1)[-1] for c in bound_caps}
    rows = []
    raw_only = set()
    in_season = []
    for entry in entries:
        doc = entry["doc"]
        if doc is None:
            rows.append({"identity": entry["dir"], "problem": entry["problem"]})
            continue
        caps = doc.get("captures") or []
        pairs = {(str(c.get("team_season_id")), c.get("raw_sha256")) for c in caps}
        if entry["dir"] == bound_identity:
            relation = "BOUND"
        elif pairs == bound_pairs:
            relation = "EQUAL"
        elif pairs < bound_pairs:
            relation = "SUBSET"
        elif pairs > bound_pairs:
            relation = "SUPERSET"
        elif pairs & bound_pairs:
            relation = "OVERLAP"
        else:
            relation = "DISJOINT"
        absent = {}
        if entry["dir"] != bound_identity:
            for capture in caps:
                relative = str(capture.get("raw_relative_path") or "")
                file_name = relative.replace("\\", "/").rsplit("/", 1)[-1]
                if file_name and file_name not in bound_files:
                    raw_only.add(file_name)
                pair = (str(capture.get("team_season_id")), capture.get("raw_sha256"))
                if pair in bound_pairs or pair in absent:
                    continue
                page = read_page(ctx, relative, pair[1], season)
                parsed = page["parsed"]
                selected = parsed["selected"] if parsed is not None else None
                if parsed is None or selected is None:
                    kind = "UNPARSEABLE"
                elif selected[0] == season_label(season):
                    kind = "IN_SEASON"
                else:
                    kind = "OUT_OF_SEASON"
                item = {"team_season_id": pair[0], "raw_sha256": pair[1], "rehash_ok": page["rehash_ok"],
                        "page_season_label": selected[0] if selected else None,
                        "page_team_season_id": selected[1] if selected else None,
                        "page_org_id": parsed["org_id"] if parsed is not None else None, "kind": kind}
                absent[pair] = item
                if kind == "IN_SEASON" and item["page_org_id"]:
                    in_season.append((item["page_org_id"], season, item))
        rows.append({"identity": entry["dir"], "state": doc.get("state"), "captures": len(caps),
                     "failures": len(doc.get("failures") or []), "sha256": entry["sha256"], "relation": relation,
                     "absent": absent})
    return rows, raw_only, in_season


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
    # atomic_write: report leftover non-identity entries beside the stage roots (observation only).
    leftovers = sorted(p.name for p in canonical_dir.parent.iterdir() if not RE_HEX64.match(p.name))
    check.counts["%s_manifest" % role] = {"identity": id_dir.name, "stage": doc["stage"], "outputs": len(outputs),
                                         "headers_checked": len(headers), "issued_at_utc": manifest["issued_at_utc"],
                                         "non_identity_entries_beside_roots": leftovers[:HEAD_LIMIT]}
    info = {"manifest": manifest, "doc": doc, "identity": id_dir.name, "canonical_dir": canonical_dir,
            "data": data, "headers": headers, "path": path}
    check_manifest_runtime_and_parameters(ctx, info, role)
    return info


def check_manifest_runtime_and_parameters(ctx, info, role):
    """output_identity_scheme.runtime and the shared parameter block (V1.2)."""
    check = ctx.check("manifest_runtime_parameters")
    manifest, doc = info["manifest"], info["doc"]
    runtime = manifest.get("runtime")
    flat = json.dumps(runtime, sort_keys=True).lower() if runtime is not None else ""
    missing = [name for name in ("python", "zlib", "sqlite") if name not in flat]
    check.counts["%s_runtime" % role] = runtime
    if not isinstance(runtime, dict) or missing:
        check.disagree({"manifest": role, "identity": info["identity"], "problem": "RUNTIME_VERSIONS_NOT_RECORDED",
                        "missing": missing})
    if "runtime" in doc:
        check.disagree({"manifest": role, "identity": info["identity"],
                        "problem": "RUNTIME_INSIDE_IDENTITY_DOCUMENT"})
    recorded = []
    for where, value in (("identity_document.inputs.parameters", (doc.get("inputs") or {}).get("parameters")
                          if isinstance(doc.get("inputs"), dict) else None),
                         ("identity_document.parameters", doc.get("parameters")),
                         ("run_manifest.parameters", manifest.get("parameters"))):
        if value is None:
            continue
        recorded.append(where)
        if value != ctx.params["raw"]:
            check.disagree({"manifest": role, "identity": info["identity"], "problem": "PARAMETERS_DIFFER_FROM_CONTRACT",
                            "where": where})
    for name, header in info["headers"].items():
        if "parameters" in header:
            recorded.append("%s._header.parameters" % name)
            if header["parameters"] != ctx.params["raw"]:
                check.disagree({"manifest": role, "problem": "PARAMETERS_DIFFER_FROM_CONTRACT", "where": name})
    check.counts["%s_parameters_recorded_at" % role] = recorded


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
        failures[str(season)] = len(failure_ids)
        expected = SPEC_EXPECTED_FAILURES.get(season, 0)
        if len(failure_ids) != expected:
            check.disagree({"season": season, "failures": len(failure_ids), "spec_expected": expected})
        for code, sample in accounting_problems(doc):
            check.disagree({"season": season, "problem": code, "team_season_ids": sample})
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

    def __init__(self, ctx, manifests, pages, history_rows, history_conflicts=(), in_season_pairs=()):
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
        self.history = {(org, season): entry["value"] for (org, season), entry in history_rows.items()}
        self.history_conflict_keys = {(c["org"], c["season"]) for c in history_conflicts}
        self.superseded_in_season = collections.defaultdict(list)
        for org, season, item in in_season_pairs:
            self.superseded_in_season[(org, season)].append(item)
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
        self.logo_orgs = logo
        # Official season-selector evidence: a bound adjacent-season page naming team-season ts for season Y.
        self.selector_orgs = collections.defaultdict(set)
        for season in self.seasons:
            label = season_label(season)
            for (s, _), page in self.pages.items():
                if s in (season - 1, season + 1) and page["parsed"] is not None and page["parsed"]["org_id"]:
                    ts = page["parsed"]["season_options"].get(label)
                    if ts:
                        self.selector_orgs[(season, ts)].add(page["parsed"]["org_id"])
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
        keys = {(org, season) for (org, season) in self.graph if season in self.seasons}
        keys.update(self.failures)
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

    def raw_label(self, org, season):
        row = self.history.get((org, season))
        if row is None or not row["division"]:
            return None
        return row["division"]

    def mapped_label(self, org, season):
        raw = self.raw_label(org, season)
        return self.ctx.params["label_map"].get(raw) if raw is not None else None

    def official_membership(self, org, season):
        raw = self.raw_label(org, season)
        if raw is None or (org, season) in self.history_conflict_keys:
            return UNRESOLVED
        code = official_label_code(self.ctx, raw)
        if code is None or raw not in self.ctx.params["label_map"]:
            return UNRESOLVED
        division_i = code_is_division_i(self.ctx, code)
        return UNRESOLVED if division_i is None else (DIVISION_I if division_i else OUTSIDE)

    def org_membership(self, org, season):
        plist = self.graph.get((org, season), [])
        if len(plist) == 1 and plist[0]["parsed"]["decode_state"] == "DECODED":
            return DIVISION_I if code_is_division_i(self.ctx, plist[0]["parsed"]["code"]) else OUTSIDE
        return self.official_membership(org, season)

    def ts_org(self, season, ts):
        """Organization of a team-season: its own page, a resolved failure, an adjacent season selector naming it,
        else a unique opponent-logo organization (payload_missing_org evidence order)."""
        page = self.pages.get((season, ts))
        if page is not None and page["parsed"] is not None:
            return page["parsed"]["org_id"]
        source = self.failure_org_source.get((season, ts))
        if source:
            return source[0]
        orgs = self.selector_orgs.get((season, ts), set())
        if len(orgs) == 1:
            return next(iter(orgs))
        orgs = self.logo_orgs.get(ts, set())
        return next(iter(orgs)) if len(orgs) == 1 else None

    def ts_membership(self, season, ts):
        page = self.pages.get((season, ts))
        if page is not None and page["parsed"] is not None and page["parsed"]["decode_state"] == "DECODED":
            return DIVISION_I if code_is_division_i(self.ctx, page["parsed"]["code"]) else OUTSIDE
        org = self.ts_org(season, ts)
        return UNRESOLVED if org is None else self.official_membership(org, season)


def expected_cell(universe, org, season):
    """Re-derive an organization-keyed cell (V1.2 dispositions, conflict rules and label vocabulary)."""
    ctx = universe.ctx
    plist = universe.graph.get((org, season), [])
    fails = universe.failures.get((org, season), [])
    raw = universe.raw_label(org, season)
    mapped = universe.mapped_label(org, season)
    out = {"page": plist[0] if len(plist) == 1 else None, "pages": plist, "failure": fails[0] if len(fails) == 1
           else None, "history_label": raw, "mapped_label": mapped, "code": None, "disposition": None,
           "division_label": None, "triggers": []}
    page = out["page"]
    code = page["parsed"]["code"] if page is not None and page["parsed"]["decode_state"] == "DECODED" else None
    triggers = []
    if len(plist) > 1:
        triggers.append("DUPLICATE_ORGANIZATION_SEASON_PAGES")
    if plist and fails:
        triggers.append("FAILED_CAPTURE_WITH_BOUND_PAGE")
    if (org, season) in universe.superseded_in_season:
        triggers.append("IN_SEASON_SUPERSEDED_PAIR")
    if (org, season) in universe.history_conflict_keys:
        triggers.append("TEAM_HISTORY_VARIANTS_DISAGREE")
    if code is not None and raw is not None:
        label_code = official_label_code(ctx, raw)
        if label_code is not None and label_code != code:
            triggers.append("OFFICIAL_LABEL_DISAGREES_WITH_PAGE_CODE")
    if triggers:
        out["disposition"] = "CONFLICT"
        out["triggers"] = triggers
        out["code"] = None if "DUPLICATE_ORGANIZATION_SEASON_PAGES" in triggers else code
        out["division_label"] = page_code_label(ctx, out["code"]) if out["code"] is not None else None
        return out
    if len(fails) > 1 and not plist:
        out["disposition"] = "AMBIGUOUS_MULTIPLE_FAILED_CAPTURES"
        return out
    if page is not None:
        parsed = page["parsed"]
        if parsed["decode_state"] != "DECODED":
            out["disposition"] = "IDENTITY_UNRESOLVED"
            return out
        out["code"] = code
        out["division_label"] = page_code_label(ctx, code)
        if code_is_division_i(ctx, code):
            if page["rehash_ok"] and page["identity_ok"] and parsed["header"] is not None:
                out["disposition"] = "VERIFIED_PRESENT"
            else:
                out["disposition"] = "UNSPECIFIED_DIVISION_I_PAGE_PROBLEM"
            return out
        out["disposition"] = "NOT_APPLICABLE"
        return out
    if fails:
        out["disposition"] = "PAYLOAD_MISSING"
        return out
    if raw is not None and mapped is None:
        out["disposition"] = "IDENTITY_UNRESOLVED"  # an official label outside the parameter label map
        return out
    out["disposition"] = "SOURCE_ABSENT"
    out["division_label"] = mapped if mapped is not None else "UNKNOWN_NOT_PROJECTED"
    return out


def parse_cell_key(cell_key):
    if not isinstance(cell_key, str):
        return None
    parts = cell_key.split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        return None
    return parts[0], parts[1], int(parts[2])


# ------------------------------------------------------------------------------------- CFBD and bindings


def load_cfbd_union(ctx, check):
    """Union of the SRC-002 and Cycle30 FCS routes for the two-source seasons, by CFBD id.

    V1.3 cfbd_route_conflict: a difference in any parameters.cfbd_game_fact_fields field is a route conflict; a
    difference only in other provider fields is a metadata difference (reported, never a conflict)."""
    seasons = contract_section(ctx, "reconciliation", "two_source_seasons")
    fbs = contract_section(ctx, "input_bindings", "cfbd_fbs_route")
    fcs = contract_section(ctx, "input_bindings", "cfbd_fcs_route")
    offsets = ctx.params["offsets"]
    fact_fields = set(ctx.params["fact_fields"])
    games = {}
    route_conflicts = {}
    metadata_differences = {}
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
                if gid in games:
                    old = games[gid]
                    if old["row"] != row:
                        differing = sorted(k for k in set(old["row"]) | set(row) if old["row"].get(k) != row.get(k))
                        facts = [k for k in differing if k in fact_fields]
                        others = [k for k in differing if k not in fact_fields]
                        if facts:
                            route_conflicts[gid] = facts
                        if others:
                            metadata_differences[gid] = others
                    old["routes"].append(route)
                    continue
                games[gid] = {"id": gid, "season": season, "season_field": row.get("season"),
                              "start": row.get("startDate"), "home": str(row.get("homeId")),
                              "away": str(row.get("awayId")), "home_points": row.get("homePoints"),
                              "away_points": row.get("awayPoints"), "home_class": row.get("homeClassification"),
                              "away_class": row.get("awayClassification"), "neutral": row.get("neutralSite"),
                              "completed": row.get("completed"), "routes": [route], "row": row,
                              "candidates": candidate_local_dates(row.get("startDate"), offsets),
                              "utc_date": utc_date(row.get("startDate"))}
                count += 1
        per_season[str(season)] = count
    check.counts["cfbd_union_games_by_season"] = per_season
    check.counts["cfbd_route_conflicts_game_facts"] = len(route_conflicts)
    check.counts["cfbd_route_conflict_fields"] = counter_dict(collections.Counter(
        field for fields in route_conflicts.values() for field in fields))
    check.counts["cfbd_route_metadata_differences"] = len(metadata_differences)
    check.counts["cfbd_route_metadata_difference_fields"] = counter_dict(collections.Counter(
        field for fields in metadata_differences.values() for field in fields))
    return games, route_conflicts, metadata_differences


def fingerprint_games(universe, seasons):
    """participant_resolution.schedule_fingerprint: the organization's completed, scored page games in scope."""
    games = collections.defaultdict(list)
    for (season, ts), page in universe.pages.items():
        parsed = page["parsed"]
        if season not in seasons or parsed is None or parsed["org_id"] is None:
            continue
        own = parsed["code"] if parsed["decode_state"] == "DECODED" else None
        for row in parsed["rows"]:
            if row.get("status") != COMPLETED or row.get("p") is None or row.get("q") is None or not row.get("date"):
                continue
            opp = universe.ts_code.get(row["opp_ts"]) if row.get("opp_ts") else None
            if own not in ("11", "12") and opp not in ("11", "12"):
                continue
            games[parsed["org_id"]].append((datetime.date.fromisoformat(row["date"]), row["p"], row["q"]))
    return games


def derive_bindings(ctx, universe, cfbd, producer_rows):
    """Re-derive F[c], N and the binding rule per organization (name candidates are the producer's)."""
    params = ctx.params
    thr = params["thresholds"]
    days = params["forward_match_days"]
    two = set(contract_section(ctx, "reconciliation", "two_source_seasons"))
    games = fingerprint_games(universe, two)
    index = collections.defaultdict(list)
    for game in cfbd.values():
        hp, ap = game["home_points"], game["away_points"]
        if not is_int(hp) or not is_int(ap) or not game["candidates"]:
            continue
        index[(hp, ap)].append((game["home"], game["candidates"]))
        index[(ap, hp)].append((game["away"], game["candidates"]))
    names = {}
    for row in producer_rows:
        names[str(row.get("org_id"))] = [str(c) for c in (row.get("name_candidates") or [])]
    result = {}
    for org in set(games) | set(names):
        fingerprint = collections.Counter()
        for date, p, q in games.get(org, ()):
            hits = {team for team, candidates in index.get((p, q), ()) if within_days(candidates, (date,), days)}
            for team in hits:
                fingerprint[team] += 1
        n_games = len(games.get(org, ()))
        ranked = sorted(fingerprint.items(), key=lambda kv: (-kv[1], kv[0]))
        best_value = ranked[0][1] if ranked else 0
        unique_best = ranked[0][0] if ranked and (len(ranked) == 1 or ranked[1][1] < best_value) else None
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        candidates = names.get(org, [])

        def strict_max(team):
            return fingerprint[team] > 0 and all(fingerprint[team] > v for t, v in fingerprint.items() if t != team)

        rule, team = None, None
        if n_games > 0:
            if len(candidates) == 1:
                c = candidates[0]
                if (fingerprint[c] >= thr["name_confirmed_min_games"]
                        and fingerprint[c] >= thr["name_confirmed_min_share"] * n_games and strict_max(c)):
                    rule, team = "NAME_CONFIRMED_BY_SCHEDULE", c
            elif len(candidates) > 1:
                qualifying = [c for c in candidates if fingerprint[c] >= thr["name_confirmed_min_games"]
                              and fingerprint[c] >= thr["name_confirmed_min_share"] * n_games]
                if len(qualifying) == 1:
                    c = qualifying[0]
                    if all(fingerprint[o] < thr["collision_other_max_share"] * n_games for o in candidates if o != c) \
                            and strict_max(c):
                        rule, team = "NAME_COLLISION_DISAMBIGUATED_BY_SCHEDULE", c
            elif ranked:
                c = ranked[0][0]
                if (fingerprint[c] >= thr["fingerprint_only_min_games"]
                        and fingerprint[c] >= thr["fingerprint_only_min_share"] * n_games
                        and runner_up <= thr["fingerprint_only_runner_up_max_share"] * n_games):
                    rule, team = "SCHEDULE_FINGERPRINT_ONLY", c
        result[org] = {"n_games": n_games, "fingerprint": fingerprint, "best_value": best_value,
                       "unique_best": unique_best, "runner_up": runner_up, "name_candidates": candidates,
                       "rule": rule, "team": team, "one_to_one_broken": False}
    team_orgs = collections.defaultdict(set)
    for org, item in result.items():
        if item["team"] is not None:
            team_orgs[item["team"]].add(org)
    for team, orgs in team_orgs.items():
        if len(orgs) > 1:
            for org in orgs:
                result[org].update(rule=None, team=None, one_to_one_broken=True)
    return result


def compare_bindings(check, derived, producer_rows):
    counts = collections.Counter()
    producer = {str(row.get("org_id")): row for row in producer_rows}
    for org in sorted(set(derived) | set(producer), key=str):
        mine = derived.get(org)
        theirs = producer.get(org)
        if theirs is None:
            if mine is not None and mine["n_games"] > 0:
                check.disagree({"org_id": org, "problem": "NO_PRODUCER_BINDING_ROW", "n_games": mine["n_games"]})
            continue
        counts["compared"] += 1
        problems = []
        if theirs.get("n_games") != mine["n_games"]:
            problems.append(("n_games", mine["n_games"], theirs.get("n_games")))
        best = theirs.get("best_fingerprint")
        best_value = best[1] if isinstance(best, list) and len(best) == 2 else (0 if best is None else best)
        if best_value != mine["best_value"]:
            problems.append(("best_fingerprint.value", mine["best_value"], best))
        elif mine["unique_best"] is not None and isinstance(best, list) and str(best[0]) != mine["unique_best"]:
            problems.append(("best_fingerprint.team", mine["unique_best"], best))
        if (theirs.get("runner_up_fingerprint") or 0) != mine["runner_up"]:
            problems.append(("runner_up_fingerprint", mine["runner_up"], theirs.get("runner_up_fingerprint")))
        candidate_values = theirs.get("candidate_fingerprints") or {}
        for c in mine["name_candidates"]:
            if (candidate_values.get(c) or 0) != mine["fingerprint"][c]:
                problems.append(("candidate_fingerprints.%s" % c, mine["fingerprint"][c], candidate_values.get(c)))
        team = str(theirs["cfbd_team_id"]) if theirs.get("cfbd_team_id") is not None else None
        if team != mine["team"] or theirs.get("rule") != mine["rule"]:
            problems.append(("binding", [mine["rule"], mine["team"]], [theirs.get("rule"), team]))
        if team is not None:
            counts["producer_bound"] += 1
        if mine["team"] is not None:
            counts["validator_bound"] += 1
        for field, value, prod in problems:
            check.disagree({"org_id": org, "field": field, "validator": value, "producer": prod,
                            "n_games": mine["n_games"], "name_candidates": mine["name_candidates"]})
    check.counts.update(counter_dict(counts))
    check.counts["validator_rules"] = counter_dict(collections.Counter(str(v["rule"]) for v in derived.values()))


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
    binding_rows = None
    if "identity_bindings.jsonl.gz" in info["data"]:
        _, binding_rows = load_jsonl_output(info, "identity_bindings.jsonl.gz")
    manifest_binding = load_json_output(info, "manifest_binding.json") if "manifest_binding.json" in info[
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

    # ---- superseded census (manifest_binding_rule V1.2)
    census_check = ctx.check("superseded_census")
    census = {}
    raw_only = {}
    in_season_pairs = []
    for season in [ADJACENT_SEASON] + seasons:
        rows, files, in_season = superseded_census(ctx, season, discovery_entries(ctx, season),
                                                   manifests[season]["identity"])
        census[season] = rows
        raw_only[season] = files
        if season in seasons:
            in_season_pairs.extend(in_season)
    compare_census(census_check, census, raw_only, manifest_binding)

    pages = load_pages(ctx, manifests)
    history_rows, history_conflicts = load_team_history(ctx, inputs_check)
    delivery_conflicts = [c for c in history_conflicts if c["season"] in seasons]
    inputs_check.counts["team_history"]["conflicting_duplicates_2016_2025"] = len(delivery_conflicts)
    universe = Universe(ctx, manifests, pages, history_rows, delivery_conflicts, in_season_pairs)

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
    flagged_pages = 0
    for key, page in sorted(pages.items()):
        season, ts = key
        parsed = page["parsed"]
        code = parsed["code"] if parsed is not None and parsed["decode_state"] == "DECODED" else None
        tallies[season][code if code is not None else "none"] += 1
        if parsed is not None and parsed["ranking_link_mismatches"]:
            flagged_pages += 1
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
                "code": code,
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
        if parsed is not None and isinstance(row.get("flags"), list):
            mine_flag = bool(parsed["ranking_link_mismatches"])
            if mine_flag != ("RANKING_LINK_IDENTITY_MISMATCH" in row["flags"]):
                check.disagree({"season": season, "team_season_id": ts, "field": "flags.RANKING_LINK_IDENTITY_MISMATCH",
                                "validator": mine_flag, "producer": row["flags"]})
        if parsed is not None:
            for field, value in (("raw_codes", parsed["raw_codes"]),
                                 ("all_ranking_link_codes", parsed["all_ranking_link_codes"])):
                if field in row and sorted(row.get(field) or []) != value:
                    check.disagree({"season": season, "team_season_id": ts, "field": field, "validator": value,
                                    "producer": row.get(field), "raw_sha256": page["raw_sha256"]})
            if "ranking_links_identity_mismatched" in row:
                theirs_mismatch = row["ranking_links_identity_mismatched"]
                mine_mismatch = parsed["ranking_link_mismatches"]
                if isinstance(theirs_mismatch, bool):
                    same = theirs_mismatch == bool(mine_mismatch)
                elif isinstance(theirs_mismatch, list):
                    same = len(theirs_mismatch) == mine_mismatch
                else:
                    same = theirs_mismatch == mine_mismatch
                if not same:
                    check.disagree({"season": season, "team_season_id": ts, "field": "ranking_links_identity_mismatched",
                                    "validator": parsed["ranking_link_mismatches"],
                                    "producer": row["ranking_links_identity_mismatched"]})
    for key in sorted(set(producer_pages) - set(pages), key=str):
        check.disagree({"problem": "UNEXPECTED_PRODUCER_ROW", "season": key[0], "team_season_id": key[1]})
    check.counts["pages_parsed"] = sum(1 for p in pages.values() if p["parsed"] is not None)
    check.counts["pages_bound"] = len(pages)
    check.counts["rehash_failures"] = sum(1 for p in pages.values() if not p["rehash_ok"])
    check.counts["identity_failures"] = sum(1 for p in pages.values() if p["parsed"] is not None
                                            and not p["identity_ok"])
    check.counts["pages_with_ranking_link_identity_mismatch"] = flagged_pages
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

    by_key = collections.defaultdict(list)
    for cell in cells:
        by_key[cell.get("cell_key")].append(cell)

    # ---- check 2: expected keys
    check = ctx.check("expected_keys")
    e1 = universe.e1_keys()
    e2 = universe.e2_keys()
    e4_keys = set(universe.e4_keys())
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
    outside = 0
    for cell in cells:
        parsed_key = parse_cell_key(cell.get("cell_key"))
        if parsed_key is None or parsed_key[0] != "org":
            continue
        key = (parsed_key[1], parsed_key[2])
        if key not in independent:
            outside += 1
        sources = set(cell.get("expected_sources") or [])
        for name, keyset in (("E1", e1), ("E2", e2), ("E4", e4_keys)):
            if (name in sources) != (key in keyset):
                source_mismatch += 1
                check.disagree({"cell_key": cell.get("cell_key"), "problem": "EXPECTED_SOURCE_MEMBERSHIP",
                                "source": name, "validator": key in keyset, "producer": name in sources})
    check.counts["expected_source_membership_mismatches"] = source_mismatch
    check.counts["producer_org_cells_outside_e1_e2_e4"] = outside

    # ---- check 3: dispositions (V1.2 conflict rules and label vocabulary)
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
        if expect["disposition"] == "CONFLICT" and not cell.get("disposition_reason"):
            problems.append(("disposition_reason", expect["triggers"], cell.get("disposition_reason")))
        if cell.get("division_code_observed") != expect["code"]:
            problems.append(("division_code_observed", expect["code"], cell.get("division_code_observed")))
        if page is not None and not expect["triggers"]:
            graph_page = cell.get("graph_page") or {}
            if graph_page.get("raw_sha256") != page["raw_sha256"]:
                problems.append(("graph_page.raw_sha256", page["raw_sha256"], graph_page.get("raw_sha256")))
            if cell.get("ncaa_team_season_id") != page["ts"]:
                problems.append(("ncaa_team_season_id", page["ts"], cell.get("ncaa_team_season_id")))
            if expect["code"] is not None:
                if cell.get("division_label") != expect["division_label"]:
                    problems.append(("division_label", expect["division_label"], cell.get("division_label")))
                if cell.get("division_authority") != "GRAPH_PAGE":
                    problems.append(("division_authority", "GRAPH_PAGE", cell.get("division_authority")))
                header = page["parsed"]["header"]
                if header is not None:
                    text = "%d-%d" % (header["wins"], header["losses"]) + (
                        "-%d" % header["ties"] if header["ties"] is not None else "")
                    if cell.get("header_record_wlt") != text:
                        problems.append(("header_record_wlt", text, cell.get("header_record_wlt")))
        elif page is None and not expect["pages"]:
            if cell.get("graph_page") is not None:
                problems.append(("graph_page", None, "present"))
        if expect["failure"] is not None and not expect["triggers"] and cell.get(
                "ncaa_team_season_id") != expect["failure"]:
            problems.append(("ncaa_team_season_id", expect["failure"], cell.get("ncaa_team_season_id")))
        if expect["disposition"] == "SOURCE_ABSENT":
            if cell.get("division_label") != expect["division_label"]:
                problems.append(("division_label", expect["division_label"], cell.get("division_label")))
            authority = "OFFICIAL_TEAM_HISTORY_ROW" if expect["mapped_label"] is not None else "NONE"
            if cell.get("division_authority") != authority:
                problems.append(("division_authority", authority, cell.get("division_authority")))
        observations = cell.get("observations")
        if expect["history_label"] is not None and isinstance(observations, dict) and \
                observations.get("team_history_label") != expect["history_label"]:
            problems.append(("observations.team_history_label", expect["history_label"],
                             observations.get("team_history_label")))
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
            if expect["triggers"]:
                item["conflict_triggers"] = expect["triggers"]
            check.disagree(item)
    check.counts["derived_dispositions"] = counter_dict(derived)
    check.counts["cells"] = len(cells)
    check.counts["in_season_superseded_pairs"] = len(in_season_pairs)
    check.counts["team_history_variant_conflicts_2016_2025"] = len(delivery_conflicts)

    # ---- check 4: decoding proof (official D-III over code 3 is counted, never proof)
    check = ctx.check("decoding_proof")
    proof_labels = sorted(ctx.params["label_codes"])
    overlap = collections.Counter()
    agreement = collections.Counter()
    code3 = []
    for (org, season), row in sorted(universe.history.items()):
        if season not in seasons or not row["division"]:
            continue
        code = universe.code.get((org, season))
        if code is None:
            continue
        label = row["division"]
        if label in ctx.params["label_codes"]:
            overlap[label] += 1
            if ctx.params["label_codes"][label] == code:
                agreement[label] += 1
            else:
                check.disagree({"org": org, "season": season, "team_history_label": label, "page_code": code,
                                "raw_sha256": universe.graph[(org, season)][0]["raw_sha256"]})
        elif official_label_code(ctx, label) == "3" and code == "3":
            code3.append({"org": org, "season": season})
    code3_keys = {(row["org"], row["season"]) for row in code3}
    for cell in cells:
        parsed_key = parse_cell_key(cell.get("cell_key"))
        if parsed_key is None or parsed_key[0] != "org":
            continue
        key = (parsed_key[1], parsed_key[2])
        if (key in code3_keys) != has_marker(cell.get("flags"), "OFFICIAL_D_III_OVER_CODE_3"):
            check.disagree({"cell_key": cell.get("cell_key"), "field": "flags.OFFICIAL_D_III_OVER_CODE_3",
                            "validator": key in code3_keys, "producer": cell.get("flags")})
    total = sum(overlap.values())
    check.counts.update(overlap_total=total, overlap_by_label=counter_dict(overlap), proof_labels=proof_labels,
                        agreement_by_label=counter_dict(agreement), code_3_overlap_count=len(code3),
                        code_3_overlap_head=code3[:HEAD_LIMIT])
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
        for key, value in proof.items():
            if "code_3" in key and isinstance(value, dict) and "count" in value and value["count"] != len(code3):
                check.disagree({"problem": "PRODUCER_CODE_3_OVERLAP", "validator": len(code3), "producer": value})
            if "code_3" in key and isinstance(value, list) and len(value) != len(code3):
                check.disagree({"problem": "PRODUCER_CODE_3_OVERLAP", "validator": len(code3),
                                "producer_rows": len(value)})

    # ---- check 5: identity bindings (schedule fingerprint on CFBD local dates)
    check = ctx.check("identity_bindings")
    if binding_rows is None:
        check.disagree({"problem": "IDENTITY_BINDINGS_OUTPUT_ABSENT"})
    else:
        cfbd, _, _ = load_cfbd_union(ctx, check)
        compare_bindings(check, derive_bindings(ctx, universe, cfbd, binding_rows), binding_rows)

    # ---- check 6: totals
    check = ctx.check("totals")
    vocabulary = set(contract_section(ctx, "program_season_dispositions"))
    duplicates = [key for key, rows in by_key.items() if len(rows) > 1]
    for key in duplicates:
        check.disagree({"problem": "DUPLICATE_CELL_KEY", "cell_key": key, "rows": len(by_key[key])})
    recount = collections.defaultdict(lambda: {"cells": 0, "by_disposition": collections.Counter(),
                                               "division_i": collections.Counter()})
    division_i_labels = [entry.get("label") for entry in contract_section(ctx, "division_decoding", "table").values()
                         if isinstance(entry, dict) and entry.get("division_i")]
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
        if cell.get("division_label") in division_i_labels:
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

    # ---- check 7: transitions (observed and across unobserved seasons)
    check = ctx.check("transitions")
    observed = {}
    across = {}
    per_org = collections.defaultdict(dict)
    for (org, season), code in universe.code.items():
        if season in seasons:
            per_org[org][season] = code
    for org, codes in per_org.items():
        ordered = sorted(codes)
        for first, second in zip(ordered, ordered[1:]):
            if codes[first] == codes[second]:
                continue
            if second - first == 1:
                observed[(org, second)] = (codes[first], codes[second])
            else:
                across[(org, second)] = (codes[first], codes[second], list(range(first + 1, second)))
    flagged = set()
    flagged_across = {}
    for cell in cells:
        parsed_key = parse_cell_key(cell.get("cell_key"))
        if parsed_key is None:
            continue
        key = (parsed_key[1], parsed_key[2])
        if cell.get("transition_observed") is True:
            flagged.add(key)
        value = cell.get("transition_across_unobserved")
        if value:
            flagged_across[key] = value
    for key in sorted(set(observed) | flagged, key=lambda k: (k[1], k[0])):
        if (key in observed) != (key in flagged):
            check.disagree({"org": key[0], "season": key[1], "kind": "TRANSITION_OBSERVED",
                            "validator": observed.get(key), "producer_transition_observed": key in flagged})
    for key in sorted(set(across) | set(flagged_across), key=lambda k: (k[1], k[0])):
        mine = across.get(key)
        theirs = flagged_across.get(key)
        if (mine is None) != (theirs is None):
            check.disagree({"org": key[0], "season": key[1], "kind": "TRANSITION_ACROSS_UNOBSERVED_SEASON",
                            "validator": mine, "producer": theirs})
            continue
        listed = unobserved_seasons_of(theirs)
        if listed is not None and listed != mine[2]:
            check.disagree({"org": key[0], "season": key[1], "kind": "TRANSITION_ACROSS_UNOBSERVED_SEASON",
                            "field": "unobserved_seasons", "validator": mine[2], "producer": theirs})
        if isinstance(theirs, dict):
            expected = {"from_code": mine[0], "to_code": mine[1], "from_season": mine[2][0] - 1}
            for field, value in expected.items():
                if field in theirs and theirs[field] != value:
                    check.disagree({"org": key[0], "season": key[1], "kind": "TRANSITION_ACROSS_UNOBSERVED_SEASON",
                                    "field": field, "validator": value, "producer": theirs[field]})
    for cell in cells:
        parsed_key = parse_cell_key(cell.get("cell_key"))
        if parsed_key is None:
            continue
        key = (parsed_key[1], parsed_key[2])
        if (key in across) != has_marker(cell.get("flags"), "TRANSITION_ACROSS_UNOBSERVED_SEASON"):
            check.disagree({"cell_key": cell.get("cell_key"), "field": "flags.TRANSITION_ACROSS_UNOBSERVED_SEASON",
                            "validator": key in across, "producer": cell.get("flags")})
    if transitions_rows is not None:
        rows_observed, rows_across = {}, {}
        for row in transitions_rows:
            key = (str(row.get("ncaa_org_id")), row.get("season"))
            value = (row.get("from_code"), row.get("to_code"))
            if has_marker(row, "TRANSITION_ACROSS_UNOBSERVED_SEASON") or any(
                    "unobserved" in str(k).lower() and row[k] for k in row):
                rows_across[key] = value
                mine = across.get(key)
                if mine is not None and (row.get("from_season", mine[2][0] - 1) != mine[2][0] - 1 or (
                        "unobserved_seasons" in row and sorted(row["unobserved_seasons"] or []) != mine[2])):
                    check.disagree({"org": key[0], "season": key[1], "kind": "ACROSS_UNOBSERVED_ROW_SEASONS",
                                    "validator": {"from_season": mine[2][0] - 1, "unobserved_seasons": mine[2]},
                                    "producer": row})
            else:
                rows_observed[key] = value
                if "kind" in row and row["kind"] != "TRANSITION_OBSERVED":
                    check.disagree({"org": key[0], "season": key[1], "field": "kind", "producer": row["kind"]})
                if "from_season" in row and row["from_season"] != key[1] - 1:
                    check.disagree({"org": key[0], "season": key[1], "field": "from_season",
                                    "validator": key[1] - 1, "producer": row["from_season"]})
        for key in sorted(set(observed) | set(rows_observed), key=lambda k: (str(k[1]), k[0])):
            if observed.get(key) != rows_observed.get(key):
                check.disagree({"org": key[0], "season": key[1], "validator": observed.get(key),
                                "producer_transitions_row": rows_observed.get(key)})
        mine_across = {key: value[:2] for key, value in across.items()}
        for key in sorted(set(mine_across) | set(rows_across), key=lambda k: (str(k[1]), k[0])):
            if mine_across.get(key) != rows_across.get(key):
                check.disagree({"org": key[0], "season": key[1], "kind": "ACROSS_UNOBSERVED_ROW",
                                "validator": mine_across.get(key), "producer_transitions_row": rows_across.get(key)})
    check.counts["transitions_observed"] = len(observed)
    check.counts["transitions_observed_by_season"] = counter_dict(collections.Counter(k[1] for k in observed))
    check.counts["transitions_across_unobserved"] = len(across)
    check.counts["transitions_across_unobserved_head"] = [
        {"org": k[0], "season": k[1], "from": v[0], "to": v[1], "unobserved_seasons": v[2]}
        for k, v in sorted(across.items(), key=lambda kv: (kv[0][1], kv[0][0]))][:HEAD_LIMIT]


def unobserved_seasons_of(value):
    """Find the list of unobserved seasons in a producer transition_across_unobserved value, if it carries one."""
    if isinstance(value, list) and all(is_int(v) for v in value):
        return sorted(value)
    if isinstance(value, dict):
        for key, item in value.items():
            if "unobserved" in str(key).lower() and isinstance(item, list) and all(is_int(v) for v in item):
                return sorted(item)
    return None


def compare_census(check, census, raw_only, manifest_binding):
    seasons_doc = manifest_binding.get("seasons") if isinstance(manifest_binding, dict) else None
    counts = collections.Counter()
    if not isinstance(seasons_doc, dict):
        check.disagree({"problem": "MANIFEST_BINDING_OUTPUT_ABSENT_OR_MALFORMED"})
    for season, rows in sorted(census.items()):
        theirs_season = (seasons_doc or {}).get(str(season)) or {}
        theirs_rows = {row.get("identity"): row for row in theirs_season.get("census") or [] if isinstance(row, dict)}
        for row in rows:
            counts["manifests"] += 1
            counts["relation_%s" % row.get("relation")] += 1
            theirs = theirs_rows.pop(row["identity"], None)
            if theirs is None:
                check.disagree({"season": season, "identity": row["identity"], "problem": "MANIFEST_NOT_IN_CENSUS"})
                continue
            for field in ("relation", "state", "captures", "sha256"):
                if field in row and theirs.get(field) != row[field]:
                    check.disagree({"season": season, "identity": row["identity"], "field": field,
                                    "validator": row[field], "producer": theirs.get(field)})
            absent = row.get("absent") or {}
            counts["absent_pairs"] += len(absent)
            listed = {tuple(pair) for pair in theirs.get("pairs_absent_from_bound") or [] if isinstance(pair, list)}
            if listed != set(absent):
                check.disagree({"season": season, "identity": row["identity"], "field": "pairs_absent_from_bound",
                                "validator": sorted(absent), "producer": sorted(listed)})
            classified = {(str(item.get("team_season_id")), item.get("raw_sha256")): item
                          for item in theirs.get("pairs_absent_classified") or [] if isinstance(item, dict)}
            for pair, mine in absent.items():
                counts["absent_%s" % mine["kind"]] += 1
                item = classified.get(pair)
                if item is None:
                    check.disagree({"season": season, "identity": row["identity"], "pair": list(pair),
                                    "problem": "ABSENT_PAIR_NOT_CLASSIFIED"})
                    continue
                expected = {"state": "CONFLICT", "rehash_ok": mine["rehash_ok"],
                            "page_season_label": mine["page_season_label"],
                            "page_team_season_id": mine["page_team_season_id"], "page_org_id": mine["page_org_id"]}
                for field, value in expected.items():
                    if item.get(field) != value:
                        check.disagree({"season": season, "identity": row["identity"], "pair": list(pair),
                                        "field": field, "validator": value, "producer": item.get(field)})
                if mine["kind"] == "OUT_OF_SEASON" and has_marker(item.get("classification"), "IN_SEASON"):
                    check.disagree({"season": season, "pair": list(pair), "field": "classification",
                                    "validator": mine["kind"], "producer": item.get("classification")})
        for identity in theirs_rows:
            check.disagree({"season": season, "identity": identity, "problem": "CENSUS_ROW_FOR_UNKNOWN_MANIFEST"})
        theirs_raw = theirs_season.get("raw_only_in_non_bound")
        if isinstance(theirs_raw, list) and set(theirs_raw) != raw_only.get(season, set()):
            check.disagree({"season": season, "field": "raw_only_in_non_bound",
                            "validator": sorted(raw_only.get(season, set()))[:20], "producer": sorted(theirs_raw)[:20]})
    check.counts.update(counter_dict(counts))


# ----------------------------------------------------------------------------------------- stage: contest


def summarize_observations(observations, spring):
    """Game-grain values from mirror observations; disagreeing values become null (V1.2 mirror_disagreement)."""
    participants = set()
    points = {}
    score_conflict = False
    neutral = False
    home_claims = set()
    seasons = set()
    dates = set()
    statuses = set()
    ext_names = set()
    for page, row in observations:
        team = page["ts"]
        opp = row["opp_ts"] if row.get("opp_ts") else "EXT"
        if opp == "EXT":
            ext_names.add(name_key(row.get("opp_name")))
        participants.add(team)
        participants.add(opp)
        seasons.add(page["season"])
        if row.get("date"):
            dates.add(row["date"])
        statuses.add(row.get("status"))
        if row.get("status") == COMPLETED and row.get("p") is not None:
            for side, value in ((team, row["p"]), (opp, row["q"])):
                if side in points and points[side] != value:
                    score_conflict = True
                points.setdefault(side, value)
        if row.get("neutral_site"):
            neutral = True
        home_claims.add(opp if row.get("away") else team)
    site_disagree = False
    if neutral:
        site = "NEUTRAL"
    elif len(home_claims) == 1:
        site = next(iter(home_claims))
    else:
        site = "UNKNOWN"
        site_disagree = True
    date_values = sorted(dates)
    status = next(iter(statuses)) if len(statuses) == 1 else MIRROR
    season = min(seasons) if seasons else None
    if season == 2020:
        parsed_dates = [datetime.date.fromisoformat(d) for d in date_values]
        if not parsed_dates:
            term = "UNRESOLVED"
        elif all(d >= spring for d in parsed_dates):
            term = "SPRING"
        elif all(d < spring for d in parsed_dates):
            term = "FALL"
        else:
            term = "UNRESOLVED"
    else:
        term = "FALL"
    mirror = score_conflict or len(statuses) > 1 or len(date_values) > 1 or site_disagree
    return {"participants": participants, "points": points if status == COMPLETED and not score_conflict else {},
            "raw_points": points, "score_conflict": score_conflict, "site": site, "site_disagree": site_disagree,
            "seasons": seasons, "season": season, "dates": date_values, "statuses": statuses, "status": status,
            "contest_date": date_values[0] if len(date_values) == 1 else None, "term": term,
            "mirror_disagreement": mirror, "observations": len(observations), "ext_names": ext_names,
            "obs": observations}


def build_graph_contests(universe, seasons):
    linked = collections.defaultdict(list)
    nolink = collections.defaultdict(list)
    for (season, ts), page in universe.pages.items():
        parsed = page["parsed"]
        if season not in seasons or parsed is None:
            continue
        for row in parsed["rows"]:
            if row.get("contest_id"):
                linked[row["contest_id"]].append((page, row))
            else:
                opp = row["opp_ts"] if row.get("opp_ts") else "EXT:" + name_key(row.get("opp_name"))
                nolink[(season, row.get("date"), frozenset((ts, opp)))].append((page, row))
    spring = universe.ctx.params["spring"]
    contests = {}
    for cid, observations in linked.items():
        item = summarize_observations(observations, spring)
        item.update(kind="ncaa", key=("ncaa", cid), producer_key="ncaa:%s" % cid, nolink_tokens=None)
        contests[item["key"]] = item
    for group, observations in nolink.items():
        item = summarize_observations(observations, spring)
        item.update(kind="nolink", key=("nolink",) + group, producer_key=None, nolink_tokens=group[2])
        contests[item["key"]] = item
    for item in contests.values():
        season = item["season"]
        item["memberships"] = {}
        item["orgs"] = {}
        for token in item["participants"]:
            if token == "EXT":
                item["memberships"][token] = NON_NCAA
                item["orgs"][token] = None
            else:
                item["memberships"][token] = universe.ts_membership(season, token)
                item["orgs"][token] = universe.ts_org(season, token)
        item["in_population"] = any(m in (DIVISION_I, UNRESOLVED) for m in item["memberships"].values())
        item["participants_inconsistent"] = len(item["participants"]) != 2
        external = sorted(item["ext_names"])
        item["pair_tokens"] = frozenset(
            [t for t in item["participants"] if t != "EXT"] + ["EXT:" + n for n in external])
    groups = collections.defaultdict(set)
    for key, item in contests.items():
        for date in item["dates"]:
            groups[(item["season"], item["pair_tokens"], date)].add(key)
    for item in contests.values():
        item["duplicate_pair_date"] = False
        item["duplicate_peers"] = set()
    for keys in groups.values():
        if len(keys) > 1:
            for key in keys:
                contests[key]["duplicate_pair_date"] = True
                contests[key]["duplicate_peers"].update(k for k in keys if k != key)
    return contests


def oriented_points(item, token_a, token_b):
    points = item["points"]
    if token_a not in points or token_b not in points:
        return None
    return points[token_a], points[token_b]


class Matching:
    """Independent forward matching, same-pair rule and CFBD-only scope for the two-source seasons."""

    def __init__(self, ctx, universe, contests, cfbd, bindings, route_conflicts):
        self.ctx = ctx
        self.universe = universe
        self.contests = contests
        self.cfbd = cfbd
        self.route_conflicts = route_conflicts
        self.days = ctx.params["forward_match_days"]
        self.window = ctx.params["window_days"]
        self.two = set(contract_section(ctx, "reconciliation", "two_source_seasons"))
        self.org_team = {org: item["team"] for org, item in bindings.items() if item["team"] is not None}
        self.team_org = {team: org for org, team in self.org_team.items()}
        by_pair = collections.defaultdict(list)
        by_team = collections.defaultdict(list)
        for game in cfbd.values():
            by_pair[(game["season"], frozenset((game["home"], game["away"])))].append(game)
            by_team[(game["season"], game["home"])].append(game)
            by_team[(game["season"], game["away"])].append(game)
        self.contest_cands = {}
        self.match_kind = {}
        self.ambiguous_single = {}
        self.game_contests = collections.defaultdict(set)
        self.date_missing = set()
        for key, item in contests.items():
            if not item["in_population"] or item["season"] not in self.two:
                continue
            dates = [datetime.date.fromisoformat(d) for d in item["dates"]]
            if not dates:
                self.date_missing.add(key)
                continue
            tokens = sorted(item["participants"])
            teams = {t: self.org_team.get(item["orgs"].get(t)) for t in tokens if t != "EXT"}
            bound = [t for t in tokens if teams.get(t)]
            cands = []
            if len(tokens) == 2 and len(bound) == 2 and teams[tokens[0]] != teams[tokens[1]]:
                pair = frozenset((teams[tokens[0]], teams[tokens[1]]))
                cands = [g for g in by_pair.get((item["season"], pair), ()) if within_days(g["candidates"], dates, self.days)]
                self.match_kind[key] = "PAIR"
            elif len(tokens) == 2 and len(bound) == 1:
                token = bound[0]
                other = tokens[1] if tokens[0] == token else tokens[0]
                score = oriented_points(item, token, other)
                team = teams[token]
                if score is not None:
                    found = []
                    for g in by_team.get((item["season"], team), ()):
                        if not within_days(g["candidates"], dates, self.days):
                            continue
                        mine = (g["home_points"], g["away_points"]) if g["home"] == team else (
                            g["away_points"], g["home_points"])
                        if mine == score:
                            found.append(g)
                    if len(found) == 1:
                        cands = found
                        self.match_kind[key] = "SINGLE_BOUND"
                    elif len(found) > 1:
                        self.ambiguous_single[key] = [g["id"] for g in found]
            self.contest_cands[key] = [g["id"] for g in cands]
            for g in cands:
                self.game_contests[g["id"]].add(key)
        # same pair + same score outside the window (V1.2)
        self.absorbed = {}
        self.absorbing = {}
        self.possible_duplicate = {}
        unmatched_games = [g for g in cfbd.values() if not self.game_contests.get(g["id"])]
        qualifying_for_contest = collections.defaultdict(list)
        candidates_for_game = {}
        for game in unmatched_games:
            orgs = (self.team_org.get(game["home"]), self.team_org.get(game["away"]))
            if None in orgs or orgs[0] == orgs[1] or not is_int(game["home_points"]) or not is_int(game["away_points"]):
                continue
            found = []
            for key, item in contests.items():
                if item["season"] != game["season"] or not item["in_population"] or self.contest_cands.get(key):
                    continue
                token_of = {item["orgs"].get(t): t for t in item["participants"] if t != "EXT"}
                if set(token_of) != set(orgs) or len(item["participants"]) != 2:
                    continue
                score = oriented_points(item, token_of[orgs[0]], token_of[orgs[1]])
                if score != (game["home_points"], game["away_points"]):
                    continue
                dates = [datetime.date.fromisoformat(d) for d in item["dates"]]
                if dates and within_days(game["candidates"], dates, self.window):
                    found.append(key)
            if found:
                candidates_for_game[game["id"]] = found
                for key in found:
                    qualifying_for_contest[key].append(game["id"])
        for gid, found in candidates_for_game.items():
            if len(found) == 1 and len(qualifying_for_contest[found[0]]) == 1:
                self.absorbed[gid] = found[0]
                self.absorbing[found[0]] = gid
            else:
                self.possible_duplicate[gid] = found
        # CFBD-only scope (cfbd_only_row)
        self.cfbd_only = {}
        self.out_of_scope = {}
        for game in cfbd.values():
            gid = game["id"]
            if self.game_contests.get(gid) or gid in self.absorbed:
                continue
            sides = []
            for team, cls in ((game["home"], game["home_class"]), (game["away"], game["away_class"])):
                org = self.team_org.get(team)
                membership = universe.org_membership(org, game["season"]) if org is not None else UNRESOLVED
                sides.append({"team": team, "org": org, "membership": membership, "class": cls})
            via_di = any(s["org"] is not None and s["membership"] == DIVISION_I for s in sides)
            via_unresolved = any(s["membership"] == UNRESOLVED and s["class"] in ("fbs", "fcs") for s in sides)
            if via_di or via_unresolved:
                self.cfbd_only[gid] = {"sides": sides, "flag_required": not via_di}
            else:
                self.out_of_scope[gid] = sides

    def one_to_one(self, key):
        cands = self.contest_cands.get(key) or []
        return len(cands) == 1 and len(self.game_contests.get(cands[0], ())) == 1


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
    _, binding_rows = load_jsonl_output(m1, "identity_bindings.jsonl.gz")
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
    manifests = load_bound_manifests(ctx, [ADJACENT_SEASON] + seasons, inputs_check)
    pages = load_pages(ctx, manifests)
    history_rows, history_conflicts = load_team_history(ctx, inputs_check)
    delivery_conflicts = [c for c in history_conflicts if c["season"] in seasons]
    universe = Universe(ctx, manifests, pages, history_rows, delivery_conflicts)
    cfbd, route_conflicts, metadata_differences = load_cfbd_union(ctx, inputs_check)
    contest_summary = load_json_output(info, "season_summary.json")
    inputs_check.counts["pages_parsed"] = sum(1 for p in pages.values() if p["parsed"] is not None)
    inputs_check.counts["rehash_failures"] = sum(1 for p in pages.values() if not p["rehash_ok"])

    derived = derive_bindings(ctx, universe, cfbd, binding_rows)
    graph = build_graph_contests(universe, set(seasons))
    matching = Matching(ctx, universe, graph, cfbd, derived, route_conflicts)
    ts_code = universe.ts_code

    by_key = {}
    duplicate_keys = []
    for contest in contests:
        key = contest.get("contest_key")
        if key in by_key:
            duplicate_keys.append(key)
        by_key[key] = contest
    producer_nolink = {}
    for key, contest in by_key.items():
        if isinstance(key, str) and key.startswith("nolink:"):
            tokens = []
            for side in ("a", "b"):
                ts = contest.get("%s_team_season_id" % side)
                tokens.append(str(ts) if ts is not None else "EXT:" + name_key(contest.get("%s_team_name" % side)))
            producer_nolink[(contest.get("season"), contest.get("contest_date"), frozenset(tokens))] = key
    for item in graph.values():
        if item["kind"] == "nolink":
            item["producer_key"] = producer_nolink.get((item["key"][1], item["key"][2], item["key"][3]))
    graph_by_producer = {item["producer_key"]: item for item in graph.values() if item["producer_key"]}

    # ---- check 1: contest reconstruction (graph contests, V1.2 game-grain rules)
    check = ctx.check("contest_reconstruction")
    vocabulary = set(ctx.params["vocabulary"])
    for key in duplicate_keys:
        check.disagree({"problem": "DUPLICATE_CONTEST_KEY", "contest_key": key})
    counts = collections.Counter()
    for item in sorted(graph.values(), key=lambda i: (str(i["season"]), str(i["key"]))):
        counts["%s_contests_raw" % item["kind"]] += 1
        if not item["in_population"]:
            if item["producer_key"] and item["producer_key"] in by_key:
                check.disagree({"contest_key": item["producer_key"], "problem": "PRODUCER_CONTEST_OUTSIDE_POPULATION",
                                "memberships": item["memberships"]})
            continue
        counts["%s_contests_in_population" % item["kind"]] += 1
        for flag, present in (("mirror_disagreement", item["mirror_disagreement"]),
                              ("duplicate_pair_date", item["duplicate_pair_date"]),
                              ("participants_inconsistent", item["participants_inconsistent"])):
            if present:
                counts["raw_%s" % flag] += 1
        theirs = by_key.get(item["producer_key"]) if item["producer_key"] else None
        evidence = [page["raw_sha256"] for page, _ in item["obs"]][:4]
        if theirs is None:
            check.disagree({"contest": str(item["key"]) if item["kind"] == "nolink" else item["producer_key"],
                            "problem": "POPULATION_CONTEST_MISSING", "memberships": item["memberships"],
                            "raw_sha256": evidence})
            continue
        counts["compared"] += 1
        problems = []
        tokens = {"a": None, "b": None}
        for side in ("a", "b"):
            ts = theirs.get("%s_team_season_id" % side)
            tokens[side] = str(ts) if ts is not None else "EXT"
        if not item["participants_inconsistent"]:
            if set(tokens.values()) != item["participants"]:
                problems.append(("participants", sorted(item["participants"]), sorted(tokens.values())))
            else:
                for side in ("a", "b"):
                    token = tokens[side]
                    expected_points = item["points"].get(token) if item["points"] else None
                    if theirs.get("%s_points" % side) != expected_points:
                        problems.append(("%s_points" % side, expected_points, theirs.get("%s_points" % side)))
                    if token != "EXT" and theirs.get("%s_division_code" % side) != ts_code.get(token):
                        problems.append(("%s_division_code" % side, ts_code.get(token),
                                         theirs.get("%s_division_code" % side)))
                    if theirs.get("%s_membership" % side) != item["memberships"][token]:
                        problems.append(("%s_membership" % side, item["memberships"][token],
                                         theirs.get("%s_membership" % side)))
                site = item["site"]
                if site not in ("NEUTRAL", "UNKNOWN"):
                    site = "HOME_A" if tokens["a"] == site else "HOME_B"
                if theirs.get("site") != site:
                    problems.append(("site", site, theirs.get("site")))
        if theirs.get("contest_status") != item["status"]:
            problems.append(("contest_status", item["status"], theirs.get("contest_status")))
        if theirs.get("contest_status") not in vocabulary:
            problems.append(("contest_status_vocabulary", sorted(vocabulary), theirs.get("contest_status")))
        if item["status"] != COMPLETED and theirs.get("competitive") is not False:
            problems.append(("competitive", False, theirs.get("competitive")))
        if item["status"] == COMPLETED and not item["mirror_disagreement"] and theirs.get("competitive") is not True:
            problems.append(("competitive", True, theirs.get("competitive")))
        if theirs.get("season") != item["season"]:
            problems.append(("season", item["season"], theirs.get("season")))
        if theirs.get("contest_date") != item["contest_date"]:
            problems.append(("contest_date", item["contest_date"], theirs.get("contest_date")))
        if "contest_dates_observed" in theirs and sorted(theirs.get("contest_dates_observed") or []) != item["dates"]:
            problems.append(("contest_dates_observed", item["dates"], theirs.get("contest_dates_observed")))
        if theirs.get("term") != item["term"]:
            problems.append(("term", item["term"], theirs.get("term")))
        if theirs.get("source") != "NCAA_GRAPH":
            problems.append(("source", "NCAA_GRAPH", theirs.get("source")))
        if item["mirror_disagreement"] and theirs.get("disposition") != "CONFLICT":
            problems.append(("disposition[MIRROR_DISAGREEMENT]", "CONFLICT", theirs.get("disposition")))
        dup_flag = "DUPLICATE_PAIR_DATE" in (theirs.get("flags") or []) or contest_marks(theirs, "DUPLICATE_PAIR_DATE")
        if item["duplicate_pair_date"] != dup_flag:
            problems.append(("flags.DUPLICATE_PAIR_DATE", item["duplicate_pair_date"], theirs.get("flags")))
        if item["duplicate_pair_date"] and theirs.get("disposition") != "CONFLICT":
            problems.append(("disposition[DUPLICATE_PAIR_DATE]", "CONFLICT", theirs.get("disposition")))
        if item["participants_inconsistent"] and (theirs.get("disposition") != "CONFLICT" or not contest_marks(
                theirs, "CONTEST_PARTICIPANTS_INCONSISTENT")):
            problems.append(("CONTEST_PARTICIPANTS_INCONSISTENT", "CONFLICT", theirs.get("disposition")))
        if not item["dates"] and not (item["mirror_disagreement"] or item["duplicate_pair_date"]
                                      or item["participants_inconsistent"]):
            if theirs.get("disposition") != "CANDIDATE_ONLY" or not contest_marks(theirs, "CONTEST_DATE_MISSING") \
                    or theirs.get("cfbd_game_ids"):
                problems.append(("CONTEST_DATE_MISSING", "CANDIDATE_ONLY", theirs.get("disposition")))
        if item["score_conflict"] != bool(theirs.get("mirror_scores_observed")):
            problems.append(("mirror_scores_observed", "retained" if item["score_conflict"] else None,
                             theirs.get("mirror_scores_observed")))
        if (len(item["statuses"]) > 1) != bool(theirs.get("contest_statuses_observed")):
            problems.append(("contest_statuses_observed", sorted(str(s) for s in item["statuses"]) if len(
                item["statuses"]) > 1 else None, theirs.get("contest_statuses_observed")))
        if item["duplicate_pair_date"]:
            peers = sorted(str(graph[k]["producer_key"]) for k in item["duplicate_peers"])
            if sorted(str(k) for k in theirs.get("duplicate_pair_date_keys") or []) != peers:
                problems.append(("duplicate_pair_date_keys", peers, theirs.get("duplicate_pair_date_keys")))
        elif theirs.get("duplicate_pair_date_keys"):
            problems.append(("duplicate_pair_date_keys", None, theirs.get("duplicate_pair_date_keys")))
        include_flag = contest_marks(theirs, "INCLUDED_FOR_UNRESOLVED_DIVISION_I_MEMBERSHIP")
        needs_flag = DIVISION_I not in item["memberships"].values()
        if needs_flag and not include_flag:
            problems.append(("flags.INCLUDED_FOR_UNRESOLVED_DIVISION_I_MEMBERSHIP", True, theirs.get("flags")))
        for field, value, producer in problems:
            check.disagree({"contest_key": item["producer_key"], "field": field, "validator": value,
                            "producer": producer, "raw_sha256": evidence})
    for key, contest in by_key.items():
        if contest.get("source") == "NCAA_GRAPH" and key not in graph_by_producer:
            check.disagree({"contest_key": key, "problem": "PRODUCER_CONTEST_NOT_IN_RAW_PAGES"})
        if isinstance(key, str) and key.startswith("ncaa:") and contest.get("ncaa_contest_id") != key[5:]:
            check.disagree({"contest_key": key, "field": "ncaa_contest_id", "producer": contest.get("ncaa_contest_id")})
        if contest.get("contest_status") not in vocabulary:
            counts["producer_status_outside_vocabulary"] += 1
    check.counts.update(counter_dict(counts))

    # ---- check 2: FCS-FCS
    check = ctx.check("fcs_fcs")
    graph_fcs = collections.Counter()
    for item in graph.values():
        parts = [p for p in item["participants"] if p != "EXT"]
        if item["in_population"] and len(item["participants"]) == 2 and len(parts) == 2 and all(
                ts_code.get(p) == "12" for p in parts):
            graph_fcs[item["season"]] += 1
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
            orgs = [matching.team_org.get(team) for team in (game["home"], game["away"])]
            if all(o is not None and universe.code.get((o, game["season"])) == "12" for o in orgs):
                cfbd_fcs[game["season"]] += 1
    per_season = {}
    for season in seasons:
        mine_total = graph_fcs[season] + cfbd_fcs[season]
        per_season[str(season)] = {"validator_graph": graph_fcs[season], "validator_cfbd_only": cfbd_fcs[season],
                                   "validator_total": mine_total, "producer_total": producer_fcs[season],
                                   "producer_graph": producer_graph_fcs[season]}
        if mine_total <= 0:
            check.disagree({"season": season, "problem": "NO_FCS_FCS_CONTESTS"})
        if mine_total != producer_fcs[season] or graph_fcs[season] != producer_graph_fcs[season]:
            check.disagree(dict(per_season[str(season)], season=season))
    check.counts["per_season"] = per_season

    # ---- check 3: orientation invariants (V1.2 views)
    check = ctx.check("orientation_invariants")
    sides = collections.defaultdict(dict)
    for row in orientations:
        key = row.get("contest_key")
        side = row.get("side")
        if side in sides[key]:
            check.disagree({"contest_key": key, "problem": "DUPLICATE_SIDE", "side": side})
        sides[key][side] = row
    complement = {"W": "L", "L": "W", "T": "T", None: None}
    view_counts = collections.Counter()
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
            for field in ("classification_pair", "disposition", "reconciliation_state", "term"):
                if row.get(field) != contest.get(field):
                    problems.append("%s_DIFFERS_FROM_CONTEST" % field.upper())
        for row, side in ((zero, "a"), (one, "b")):
            if row.get("team_season_id") != contest.get("%s_team_season_id" % side) or row.get(
                    "team_points") != contest.get("%s_points" % side):
                problems.append("SIDE_%s_NOT_CONTEST_%s" % (row.get("side"), side.upper()))
            other = "b" if side == "a" else "a"
            if "team_key" in row and (row.get("team_key") != contest.get("%s_key" % side)
                                      or row.get("opponent_key") != contest.get("%s_key" % other)):
                problems.append("KEYS_SIDE_%s_NOT_CONTEST_%s" % (row.get("side"), side.upper()))
            membership = contest.get("%s_membership" % side)
            if row.get("team_membership") != membership:
                problems.append("TEAM_MEMBERSHIP_SIDE_%s_NOT_CONTEST_%s" % (row.get("side"), side.upper()))
            view = "EXTERNAL_OPPONENT_VIEW" if membership in EXTERNAL_MEMBERSHIPS else "PARTICIPANT_VIEW"
            view_counts[view] += 1
            if row.get("view") != view:
                problems.append("VIEW_SIDE_%s_EXPECTED_%s" % (row.get("side"), view))
        for problem in sorted(set(problems)):
            check.disagree({"contest_key": key, "problem": problem})
    for key in [key for key in by_key if key not in sides]:
        check.disagree({"contest_key": key, "problem": "CONTEST_WITHOUT_ORIENTATIONS"})
    check.counts.update(orientation_rows=len(orientations), contest_keys_with_orientations=len(sides),
                        contests=len(by_key), expected_views=counter_dict(view_counts))

    # ---- check 4: single-source seasons
    check = ctx.check("single_source_seasons")
    single = set(contract_section(ctx, "reconciliation", "single_source_seasons"))
    two = set(contract_section(ctx, "reconciliation", "two_source_seasons"))
    single_state = contract_section(ctx, "reconciliation", "single_source_state")
    exposure = ctx.params["exposure"]
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
            if contest.get("source") != "NCAA_GRAPH":
                problems.append(("source", contest.get("source")))
            for field, value in problems:
                check.disagree({"contest_key": key, "season": season, "field": field, "producer": value})
        if contest.get("reconciliation_state") == reconciled_state and season not in two:
            check.disagree({"contest_key": key, "season": season, "problem": "RECONCILED_OUTSIDE_2016_2023"})
        if season not in seasons:
            check.disagree({"contest_key": key, "season": season, "problem": "SEASON_OUTSIDE_SCOPE"})
    check.counts.update(counter_dict(counts))

    references = collections.defaultdict(list)
    for contest in contests:
        for gid in contest.get("cfbd_game_ids") or []:
            references[str(gid)].append(contest.get("contest_key"))

    # ---- check 5: forward matching on CFBD local dates, same-pair rule, non-competitive and route conflicts
    check = ctx.check("forward_match")
    counts = collections.Counter()
    observations = collections.Counter()
    for key, item in graph.items():
        if not item["in_population"] or item["season"] not in two:
            continue
        theirs = by_key.get(item["producer_key"]) if item["producer_key"] else None
        if theirs is None:
            continue
        cands = matching.contest_cands.get(key) or []
        absorbed = matching.absorbing.get(key)
        expected = set(cands) | ({absorbed} if absorbed else set())
        produced = {str(g) for g in theirs.get("cfbd_game_ids") or []}
        evidence = {"contest_key": item["producer_key"], "dates": item["dates"], "validator_cfbd_ids": sorted(expected),
                    "producer_cfbd_ids": sorted(produced), "match_kind": matching.match_kind.get(key)}
        if key in matching.ambiguous_single:
            counts["single_bound_ambiguous"] += 1
            continue
        if produced - expected:
            check.disagree(dict(evidence, problem="UNJUSTIFIED_CFBD_REFERENCE"))
        if expected and not produced:
            missed = dict(evidence, problem="FORWARD_MATCH_MISSED")
            missed["cfbd"] = [{"id": g, "startDate": cfbd[g]["start"], "local_dates": [str(d) for d in
                               cfbd[g]["candidates"]], "utc_date": str(cfbd[g]["utc_date"])} for g in sorted(expected)]
            check.disagree(missed)
        triggers = []
        if item["mirror_disagreement"] or item["duplicate_pair_date"] or item["participants_inconsistent"]:
            triggers.append("GRAPH_CONFLICT")
        state = theirs.get("reconciliation_state")
        disposition = theirs.get("disposition")
        if cands:
            counts["contests_with_forward_candidates_%s" % matching.match_kind.get(key)] += 1
            game = cfbd[cands[0]]
            if not matching.one_to_one(key):
                counts["not_one_to_one_contests"] += 1
                if disposition != "CONFLICT" or not contest_marks(theirs, "NOT_ONE_TO_ONE"):
                    check.disagree(dict(evidence, problem="NOT_ONE_TO_ONE_NOT_CONFLICT", producer=[
                        disposition, theirs.get("disposition_reason")]))
                continue
            if all(abs((d - datetime.date.fromisoformat(x)).days) > matching.days for d in (game["utc_date"],)
                   for x in item["dates"]) if game["utc_date"] else False:
                observations["one_to_one_matches_missed_by_utc_date"] += 1
            if cands[0] in route_conflicts:
                counts["route_conflict_contests"] += 1
                if disposition != "CONFLICT" or not contest_marks(theirs, "CFBD_ROUTE_CONFLICT"):
                    check.disagree(dict(evidence, problem="CFBD_ROUTE_CONFLICT_NOT_MARKED",
                                        differing_fields=route_conflicts[cands[0]],
                                        producer=[state, disposition, theirs.get("disposition_reason")]))
                continue
            if matching.match_kind.get(key) == "SINGLE_BOUND":
                counts["single_bound_matches"] += 1
                if state == reconciled_state:
                    check.disagree(dict(evidence, problem="SINGLE_BOUND_PARTICIPANT_RECONCILED"))
                continue
            if item["status"] != COMPLETED:
                counts["non_competitive_matches"] += 1
                if game["completed"] is True:
                    triggers.append("NON_COMPETITIVE_AGAINST_COMPLETED_CFBD")
                    if disposition != "CONFLICT":
                        check.disagree(dict(evidence, problem="NON_COMPETITIVE_VS_COMPLETED_CFBD_NOT_CONFLICT",
                                            producer=disposition))
                elif not triggers and (disposition != "CANDIDATE_ONLY" or not contest_marks(
                        theirs, "NON_COMPETITIVE_BOTH_SOURCES")):
                    check.disagree(dict(evidence, problem="NON_COMPETITIVE_BOTH_SOURCES_NOT_CANDIDATE",
                                        producer=[disposition, theirs.get("disposition_reason")]))
                if state == reconciled_state:
                    check.disagree(dict(evidence, problem="NON_COMPETITIVE_RECONCILED"))
                continue
            tokens = sorted(item["participants"])
            team_of = {t: matching.org_team.get(item["orgs"].get(t)) for t in tokens}
            score_ok = True
            if not item["score_conflict"]:
                game_points = {game["home"]: game["home_points"], game["away"]: game["away_points"]}
                score_ok = all(item["points"].get(t) == game_points.get(team_of[t]) for t in tokens)
            site_ok = True
            if item["site"] == "NEUTRAL":
                site_ok = game["neutral"] is not False
            elif item["site"] != "UNKNOWN":
                site_ok = game["neutral"] is not True and team_of.get(item["site"]) == game["home"]
            if not score_ok:
                triggers.append("SCORE")
            if not site_ok:
                triggers.append("SITE")
            if triggers:
                counts["matched_with_conflict"] += 1
                if disposition != "CONFLICT":
                    check.disagree(dict(evidence, problem="MATCHED_CONFLICT_NOT_CONFLICT", triggers=triggers,
                                        producer=[disposition, theirs.get("disposition_reason")]))
                if state == reconciled_state:
                    check.disagree(dict(evidence, problem="CONFLICT_RECONCILED", triggers=triggers))
            else:
                counts["clean_one_to_one_matches"] += 1
                if state != reconciled_state:
                    check.disagree(dict(evidence, problem="CLEAN_MATCH_NOT_RECONCILED",
                                        producer=[state, disposition, theirs.get("disposition_reason")]))
        elif absorbed:
            counts["same_pair_same_score_absorbed"] += 1
            if disposition != "CONFLICT" or "date" not in conflict_field_names(theirs):
                check.disagree(dict(evidence, problem="SAME_PAIR_SAME_SCORE_NOT_CONFLICT_ON_DATE",
                                    producer=[disposition, theirs.get("conflict_fields")]))
        else:
            if state == reconciled_state:
                check.disagree(dict(evidence, problem="RECONCILED_WITHOUT_FORWARD_MATCH"))
    for gid, contest_keys in matching.game_contests.items():
        if "cfbd:%s" % gid in by_key:
            check.disagree({"cfbd_game_id": gid, "problem": "CFBD_ONLY_CONTEST_DESPITE_FORWARD_MATCH",
                            "ncaa_candidates": sorted(graph[k]["producer_key"] or str(k) for k in contest_keys),
                            "local_dates": [str(d) for d in cfbd[gid]["candidates"]],
                            "utc_date": str(cfbd[gid]["utc_date"])})
    for gid, key in matching.absorbed.items():
        if "cfbd:%s" % gid in by_key:
            check.disagree({"cfbd_game_id": gid, "problem": "SAME_PAIR_SAME_SCORE_BECAME_SECOND_CONTEST",
                            "ncaa_contest": graph[key]["producer_key"]})
    for gid, keys in matching.possible_duplicate.items():
        observations["possible_duplicate_games"] += 1
        row = by_key.get("cfbd:%s" % gid)
        if row is None or row.get("disposition") != "CONFLICT" or not contest_marks(row, "POSSIBLE_DUPLICATE_OF"):
            check.disagree({"cfbd_game_id": gid, "problem": "POSSIBLE_DUPLICATE_NOT_FLAGGED",
                            "ncaa_contests": sorted(str(graph[k]["producer_key"]) for k in keys),
                            "producer": None if row is None else [row.get("disposition"), row.get("flags")]})
    # reconciliation.cfbd_match_date_fields (V1.3): every one-to-one match (pair, single bound participant or same
    # pair outside the window) records cfbd_local_dates, and date_delta_days when no candidate equals a page date.
    nonzero_delta = []
    for key, item in graph.items():
        if not item["in_population"] or item["season"] not in two or not item["dates"] or not item["producer_key"]:
            continue
        contest = by_key.get(item["producer_key"])
        if contest is None:
            continue
        if matching.one_to_one(key):
            gid, kind = matching.contest_cands[key][0], matching.match_kind.get(key)
        elif key in matching.absorbing:
            gid, kind = matching.absorbing[key], "SAME_PAIR_OUTSIDE_WINDOW"
        else:
            if contest.get("cfbd_local_dates") is not None or contest.get("date_delta_days") is not None:
                ids = [str(g) for g in contest.get("cfbd_game_ids") or []]
                if len(ids) == 1 and ids[0] in cfbd and contest.get("cfbd_local_dates") is not None and contest.get(
                        "cfbd_local_dates") != [str(d) for d in cfbd[ids[0]]["candidates"]]:
                    check.disagree({"contest_key": item["producer_key"], "field": "cfbd_local_dates",
                                    "validator": [str(d) for d in cfbd[ids[0]]["candidates"]],
                                    "producer": contest.get("cfbd_local_dates")})
                observations["match_date_fields_on_non_one_to_one_contests"] += 1
            continue
        game = cfbd[gid]
        observations["one_to_one_matches_checked_for_date_fields_%s" % kind] += 1
        expected_local = [str(d) for d in game["candidates"]]
        if contest.get("cfbd_local_dates") != expected_local:
            check.disagree({"contest_key": item["producer_key"], "field": "cfbd_local_dates", "match_kind": kind,
                            "validator": expected_local, "producer": contest.get("cfbd_local_dates", "absent")})
        dates = [datetime.date.fromisoformat(d) for d in item["dates"]]
        delta = min(abs((c - d).days) for c in game["candidates"] for d in dates) if game["candidates"] else None
        expected_delta = delta if delta else None
        if contest.get("date_delta_days") != expected_delta:
            check.disagree({"contest_key": item["producer_key"], "field": "date_delta_days", "match_kind": kind,
                            "validator": expected_delta, "producer": contest.get("date_delta_days", "absent"),
                            "dates": item["dates"], "local_dates": expected_local})
        if delta:
            nonzero_delta.append(item["producer_key"])
    for key, contest in by_key.items():
        ids = [str(g) for g in contest.get("cfbd_game_ids") or []]
        if contest_marks(contest, "CFBD_ROUTE_CONFLICT") and not any(g in route_conflicts for g in ids):
            check.disagree({"contest_key": key, "problem": "CFBD_ROUTE_CONFLICT_WITHOUT_GAME_FACT_DIFFERENCE",
                            "cfbd_game_ids": ids, "metadata_only_fields": [metadata_differences.get(g) for g in ids]})
    observations["games_with_forward_match"] = len(matching.game_contests)
    observations["date_missing_contests"] = len(matching.date_missing)
    check.counts.update(counter_dict(counts))
    check.counts["observations"] = counter_dict(observations)
    check.counts["one_to_one_matches_with_nonzero_date_delta"] = sorted(nonzero_delta)[:HEAD_LIMIT]
    check.counts["route_conflict_games"] = len(route_conflicts)
    binding_diff = sum(1 for org, row in ((str(r.get("org_id")), r) for r in binding_rows)
                       if (str(row["cfbd_team_id"]) if row.get("cfbd_team_id") is not None else None)
                       != (derived.get(org) or {}).get("team"))
    check.counts["validator_bindings_differing_from_m1"] = binding_diff

    # ---- check 6: CFBD-only rows (V1.2 cfbd_only_row)
    check = ctx.check("cfbd_only_rows")
    counts = collections.Counter()
    expected_rows = set(matching.cfbd_only) | {gid for gid in matching.possible_duplicate if gid in matching.cfbd_only}
    produced_rows = {key[5:] for key in by_key if isinstance(key, str) and key.startswith("cfbd:")}
    for gid in sorted(expected_rows - produced_rows):
        game = cfbd[gid]
        check.disagree({"cfbd_game_id": gid, "season": game["season"], "problem": "IN_SCOPE_UNMATCHED_GAME_NOT_A_CONTEST",
                        "sides": matching.cfbd_only[gid]["sides"]})
    for gid in sorted(produced_rows):
        contest = by_key["cfbd:%s" % gid]
        counts["cfbd_only_contests"] += 1
        game = cfbd.get(gid)
        problems = []
        if game is None:
            check.disagree({"contest_key": "cfbd:%s" % gid, "problem": "CFBD_GAME_NOT_IN_BOUND_ROUTES"})
            continue
        if gid not in expected_rows:
            if gid in matching.out_of_scope:
                problems.append(("scope", "OUT_OF_SCOPE", matching.out_of_scope[gid]))
            elif gid in matching.game_contests or gid in matching.absorbed:
                problems.append(("scope", "MATCHED_TO_NCAA_CONTEST", None))
        if contest.get("source") != "CFBD_ONLY":
            problems.append(("source", "CFBD_ONLY", contest.get("source")))
        if [str(g) for g in contest.get("cfbd_game_ids") or []] != [gid]:
            problems.append(("cfbd_game_ids", [gid], contest.get("cfbd_game_ids")))
        if contest.get("season") != game["season"]:
            problems.append(("season", game["season"], contest.get("season")))
        for field, value in (("site", "UNKNOWN"), ("contest_status", NOT_OBSERVED), ("competitive", False),
                             ("a_points", None), ("b_points", None)):
            if contest.get(field) != value:
                problems.append((field, value, contest.get(field)))
        side_info = []
        for team, cls in ((game["home"], game["home_class"]), (game["away"], game["away_class"])):
            org = matching.team_org.get(team)
            side_key = "org:%s" % org if org is not None else "cfbdteam:%s" % team
            membership = universe.org_membership(org, game["season"]) if org is not None else UNRESOLVED
            side_info.append({"key": side_key, "team": team, "org": org, "membership": membership,
                              "code": universe.code.get((org, game["season"])) if org is not None else None})
        side_info.sort(key=lambda s: s["key"])
        for side, mine in zip(("a", "b"), side_info):
            for field, value in (("key", mine["key"]), ("cfbd_team_id", mine["team"]), ("org_id", mine["org"]),
                                 ("membership", mine["membership"]), ("division_code", mine["code"])):
                theirs = contest.get("%s_%s" % (side, field))
                if (str(theirs) if theirs is not None else None) != value:
                    problems.append(("%s_%s" % (side, field), value, theirs))
        if gid in matching.cfbd_only and matching.cfbd_only[gid]["flag_required"] and not contest_marks(
                contest, "INCLUDED_FOR_UNRESOLVED_DIVISION_I_MEMBERSHIP"):
            problems.append(("flags.INCLUDED_FOR_UNRESOLVED_DIVISION_I_MEMBERSHIP", True, contest.get("flags")))
        if (gid in route_conflicts) != contest_marks(contest, "CFBD_ROUTE_CONFLICT"):
            problems.append(("flags.CFBD_ROUTE_CONFLICT", gid in route_conflicts, contest.get("flags")))
        possible = gid in matching.possible_duplicate
        if possible != contest_marks(contest, "POSSIBLE_DUPLICATE_OF"):
            problems.append(("flags.POSSIBLE_DUPLICATE_OF", possible, contest.get("flags")))
        allowed = {"CONFLICT"} if possible else {"SOURCE_ABSENT", "IDENTITY_UNRESOLVED"}
        if contest.get("disposition") not in allowed:
            problems.append(("disposition", sorted(allowed), contest.get("disposition")))
        if contest.get("contest_date") is not None and iso_date(contest.get("contest_date")) not in game["candidates"]:
            problems.append(("contest_date", "null or a candidate local date %s" % [str(d) for d in game["candidates"]],
                             contest.get("contest_date")))
        expected_term = "FALL"
        if game["season"] == 2020:
            spring = ctx.params["spring"]
            if all(d >= spring for d in game["candidates"]):
                expected_term = "SPRING"
            elif any(d >= spring for d in game["candidates"]):
                expected_term = "UNRESOLVED"
        if contest.get("term") != expected_term:
            problems.append(("term", expected_term, contest.get("term")))
        problems.extend(cfbd_observation_problems(contest.get("cfbd_observation"), game))
        for field, value, theirs in problems:
            check.disagree({"contest_key": "cfbd:%s" % gid, "field": field, "validator": value, "producer": theirs})
    check.counts.update(counter_dict(counts))
    check.counts["validator_in_scope_unmatched_games"] = len(matching.cfbd_only)
    check.counts["validator_out_of_scope_unmatched_games"] = len(matching.out_of_scope)
    check.counts["validator_flag_required"] = sum(1 for v in matching.cfbd_only.values() if v["flag_required"])

    # ---- check 7: reconciled contests (CFBD local dates)
    check = ctx.check("reconciled_contests")
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
        if game is None:
            check.disagree({"contest_key": key, "problem": "CFBD_GAME_NOT_IN_BOUND_ROUTES", "cfbd_game_id": ids[0]})
            continue
        problems = []
        if game["season"] != contest.get("season"):
            problems.append(("season", game["season"], contest.get("season")))
        item = graph_by_producer.get(key)
        dates = [datetime.date.fromisoformat(d) for d in item["dates"]] if item else [
            d for d in (iso_date(x) for x in contest.get("contest_dates_observed") or [contest.get("contest_date")])
            if d is not None]
        if not dates or not within_days(game["candidates"], dates, ctx.params["forward_match_days"]):
            problems.append(("observed_dates_vs_cfbd_local_dates", [str(d) for d in game["candidates"]],
                             [str(d) for d in dates]))
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
        if ids[0] in route_conflicts:
            problems.append(("cfbd_route_conflict", "CONFLICT", reconciled_state))
        for side in ("a", "b"):
            org = contest.get("%s_org_id" % side)
            team = str(contest.get("%s_cfbd_team_id" % side))
            if org is None or matching.org_team.get(str(org)) != team:
                problems.append(("%s_identity_binding" % side, matching.org_team.get(str(org)), team))
        for field, mine, theirs in problems:
            check.disagree({"contest_key": key, "cfbd_game_id": ids[0], "field": field, "validator": mine,
                            "producer": theirs})
    check.counts.update(counter_dict(counts))

    # ---- check: CFBD route differences (V1.3: game-fact conflicts vs metadata-only differences)
    check = ctx.check("cfbd_route_differences")
    summary_doc = contest_summary if isinstance(contest_summary, dict) else {}
    for field, mine_map in (("cfbd_route_metadata_differences", metadata_differences),
                            ("cfbd_route_conflicts", route_conflicts)):
        theirs = summary_doc.get(field)
        if theirs is None:
            if field == "cfbd_route_metadata_differences":
                check.disagree({"field": field, "problem": "ABSENT_FROM_CONTEST_SEASON_SUMMARY"})
            continue
        if not isinstance(theirs, dict):
            check.disagree({"field": field, "problem": "NOT_AN_OBJECT", "producer": str(theirs)[:200]})
            continue
        mine_by_season = collections.defaultdict(dict)
        for gid, fields in mine_map.items():
            mine_by_season[str(cfbd[gid]["season"])][gid] = sorted(fields)
        for season in sorted(set(mine_by_season) | set(theirs)):
            produced = {}
            for entry in theirs.get(season) or []:
                if isinstance(entry, dict):
                    produced[str(entry.get("cfbd_game_id"))] = sorted(entry.get("fields") or [])
                else:
                    produced[str(entry)] = None
            mine = mine_by_season.get(season, {})
            for gid in sorted(set(mine) | set(produced)):
                if gid not in produced:
                    check.disagree({"field": field, "season": season, "cfbd_game_id": gid, "problem": "NOT_LISTED",
                                    "validator_fields": mine[gid]})
                elif gid not in mine:
                    check.disagree({"field": field, "season": season, "cfbd_game_id": gid,
                                    "problem": "LISTED_WITHOUT_RAW_DIFFERENCE", "producer_fields": produced[gid]})
                elif produced[gid] is not None and produced[gid] != mine[gid]:
                    check.disagree({"field": field, "season": season, "cfbd_game_id": gid, "problem": "FIELDS",
                                    "validator_fields": mine[gid], "producer_fields": produced[gid]})
        check.counts["%s_by_season" % field] = {season: len(v) for season, v in sorted(mine_by_season.items())}
    check.counts["fact_fields"] = ctx.params["fact_fields"]
    check.counts["games_in_both_routes"] = sum(1 for g in cfbd.values() if len(g["routes"]) > 1)

    # ---- check 8: reverse join (V1.2 scope; explicit NOT_ONE_TO_ONE multi-references)
    check = ctx.check("cfbd_reverse_join")
    reverse = collections.defaultdict(list)
    for row in reverse_rows:
        reverse[str(row.get("cfbd_game_id"))].append(row)
    counts = collections.Counter()
    not_one_to_one = collections.Counter()
    observed = []
    for gid, game in sorted(cfbd.items()):
        refs = references.get(gid, [])
        required = gid in matching.game_contests or gid in matching.absorbed or gid in matching.cfbd_only
        if not required:
            counts["unmatched_out_of_scope_games"] += 1
            if refs:
                check.disagree({"cfbd_game_id": gid, "season": game["season"], "problem": "OUT_OF_SCOPE_GAME_REFERENCED",
                                "contest_keys": refs, "sides": matching.out_of_scope.get(gid)})
            for row in reverse.get(gid, []):
                if row.get("contest_key"):
                    check.disagree({"cfbd_game_id": gid, "problem": "OUT_OF_SCOPE_REVERSE_ROW_NAMES_CONTEST",
                                    "reverse_row": row})
            continue
        counts["games_requiring_a_contest"] += 1
        if len(refs) == 0:
            counts["unmatched"] += 1
            check.disagree({"cfbd_game_id": gid, "season": game["season"], "problem": "UNMATCHED",
                            "reverse_rows": reverse.get(gid, [])[:2]})
            continue
        if len(refs) > 1:
            counts["multiply_matched"] += 1
            referencing = [by_key.get(ref) or {} for ref in refs]
            explicit = len(set(refs)) == len(refs) and all(
                contest.get("disposition") == "CONFLICT" and contest_marks(contest, "NOT_ONE_TO_ONE")
                for contest in referencing)
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
    check.counts.update(counter_dict(counts))
    check.counts["reverse_rows"] = len(reverse_rows)
    check.counts["explicit_not_one_to_one_games_by_season"] = {str(season): not_one_to_one[season]
                                                               for season in sorted(two)}
    check.counts["explicit_not_one_to_one_games_head"] = observed[:HEAD_LIMIT]

    # ---- check 9: schedule cardinality
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
        if season not in seasons or parsed is None or parsed["decode_state"] != "DECODED" or not code_is_division_i(
                ctx, parsed["code"]):
            continue
        counts["division_i_pages"] += 1
        rows = parsed["rows"]
        completed = [r for r in rows if r.get("status") == COMPLETED and not r.get("exempt")]
        header = parsed["header"]
        header_wlt = None if header is None else (header["wins"], header["losses"], header["ties"] or 0)
        by_letter = wlt(collections.Counter(r.get("letter") for r in completed))
        by_score = wlt(collections.Counter("W" if r["p"] > r["q"] else "L" if r["p"] < r["q"] else "T"
                                           for r in completed))
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
        derived_record = produced.get("derived_record")
        derived_wlt = None if not isinstance(derived_record, dict) else (
            derived_record.get("wins"), derived_record.get("losses"), derived_record.get("ties") or 0)
        if derived_wlt not in (by_letter, by_score):
            check.disagree({"season": season, "team_season_id": ts, "field": "derived_record",
                            "validator_letters": by_letter, "validator_scores": by_score, "producer": derived_record})
    check.counts.update(counter_dict(counts))
    check.counts["explicit_mismatch_cells"] = explicit_cells[:HEAD_LIMIT]
    check.counts["producer_rows"] = len(schedule_rows)
    check.counts["producer_states"] = counter_dict(collections.Counter(row.get("state") for row in schedule_rows))
    if len(schedule_rows) != counts["division_i_pages"]:
        check.disagree({"problem": "RECONCILIATION_ROW_COUNT", "producer_rows": len(schedule_rows),
                        "division_i_pages": counts["division_i_pages"]})


OBSERVATION_FIELDS = (
    ("home_id", ("homeid", "hometeamid", "homecfbdteamid", "cfbdhomeid", "cfbdhometeamid"), "home", str),
    ("away_id", ("awayid", "awayteamid", "awaycfbdteamid", "cfbdawayid", "cfbdawayteamid"), "away", str),
    ("home_points", ("homepoints", "homescore"), "home_points", None),
    ("away_points", ("awaypoints", "awayscore"), "away_points", None),
    ("completed", ("completed", "iscompleted"), "completed", None),
    ("neutral", ("neutralsite", "neutral", "isneutral"), "neutral", None),
    ("home_classification", ("homeclassification", "homeclass"), "home_class", None),
    ("away_classification", ("awayclassification", "awayclass"), "away_class", None),
    ("start", ("startdate", "startinstant", "start", "starttimeutc", "startutc"), "start", None),
)


def cfbd_observation_problems(observation, game):
    """cfbd_only_row: the provider's values are kept as observation fields (producer: 'cfbd_observation')."""
    if not isinstance(observation, dict):
        return [("cfbd_observation", "object with provider observations", observation)]
    normalized = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in observation.items()}
    problems = []
    for name, aliases, attribute, cast in OBSERVATION_FIELDS:
        found = [normalized[a] for a in aliases if a in normalized]
        expected = game[attribute]
        if not found:
            problems.append(("cfbd_observation.%s" % name, expected, "absent"))
            continue
        value = found[0]
        if cast is str:
            value = str(value) if value is not None else None
        if name == "start":
            same = value == expected or (parse_instant(value) is not None and parse_instant(value) == parse_instant(
                expected))
        else:
            same = value == expected
        if not same:
            problems.append(("cfbd_observation.%s" % name, expected, value))
    return problems


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
    load_parameters(ctx)


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
        json.dump(report, handle, indent=1, sort_keys=True, ensure_ascii=False, default=str)
        handle.write("\n")
    for name, check in checks.items():
        print("%-30s %s (%d disagreements)" % (name, check["result"], check["disagreement_count"]))
    print("result %s%s -> %s" % (result, " (%s)" % refusal if refusal else "", report_path))
    return {"PASS": 0, "FAIL": 1}.get(result, 2)


if __name__ == "__main__":
    sys.exit(main())
