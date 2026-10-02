r"""National Division I program-season and contest population, 2016-2025 (BAT-710, Cycle #38 TP38-A01-01..07).

Producer for the official national FBS/FCS program-season grain (M1), the canonical contest grain with two derived
orientations and two-source CFBD reconciliation for 2016-2023 (M2), explicitly single-source 2024-2025 contests,
parent-derived FBS/FCS subsets and the read-only query database. Everything is governed by
``configs/national_di_population_2016_2025_contract.json``; outputs are content-addressed and create-only.

Authority boundaries (contract ``non_claims``): no PIT/known-at authority, no predictive skill, no strength
comparability, no pre-2016 or 2026 completeness, no scientific trust, no Jira acceptance. Every expected cell keeps
exactly one disposition; denominators come only from the E1-E6 expected-key union, never from observed rows.

The independent validator (``tools/validate_national_di_population_2016_2025.py``) must not import this module.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import html
import io
import json
import os
import re
import sqlite3
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics.data import ncaa_contest_reconciliation

SCHEMA_VERSION = "BAS-NATIONAL-DI-POPULATION-1"
PRODUCER_VERSION = "national_di_population/1.0.0"
DB_SCHEMA_VERSION = "BAS-NATIONAL-DI-POPULATION-DB-1"
DB_FILE_NAME = "national_population.sqlite"
POPULATION = "national_di_population_2016_2025"
DELIVERY_SEASONS = tuple(range(2016, 2026))
TWO_SOURCE_SEASONS = tuple(range(2016, 2024))
SINGLE_SOURCE_SEASONS = (2024, 2025)
STAGES = ("program-season", "contest", "query-db")

PROGRAM_SEASON_DISPOSITIONS = ("VERIFIED_PRESENT", "CANDIDATE_ONLY", "IDENTITY_UNRESOLVED", "PAYLOAD_MISSING",
                               "SOURCE_ABSENT", "CONFLICT", "NOT_APPLICABLE", "NOT_YET_AUDITED")
CONTEST_DISPOSITIONS = ("VERIFIED_PRESENT", "CANDIDATE_ONLY", "IDENTITY_UNRESOLVED", "SOURCE_ABSENT", "CONFLICT",
                        "NOT_YET_AUDITED")
CONTEST_STATUSES = ("COMPLETED", "CANCELED", "NO_CONTEST", "FORFEIT", "UNSCORED", "MIRROR_DISAGREEMENT",
                    "NOT_OFFICIALLY_OBSERVED")
RECONCILED = "RECONCILED_2016_2023"
SINGLE_SOURCE = "SINGLE_SOURCE_UNRECONCILED"
EXPOSURE_2024_2025 = "EXPOSED_NOT_PROTECTED"
DIVISION_I_CODES = ("11", "12")
CODE_FORM_RE = re.compile(r"^(0|[1-9][0-9]*)(\.0)?$")
FORWARD_MATCH_DAYS = 1
CFBD_LOCAL_OFFSET_HOURS = (-4, -10)
SAME_PAIR_WINDOW_DAYS = 7
SPRING_2020_FROM = "2021-01-16"
BINDING_THRESHOLDS = {"name_confirmed_min_games": 3, "name_confirmed_min_share": 0.5, "collision_other_max_share": 0.2,
                      "fingerprint_only_min_games": 5, "fingerprint_only_min_share": 0.8,
                      "fingerprint_only_runner_up_max_share": 0.2}
E2_LABEL_MAP = {"FBS": "FBS", "FCS": "FCS", "D-II": "DII", "D-III": "DIII"}
E2_LABEL_TO_CODE = {"FBS": "11", "FCS": "12", "D-II": "2"}
RANKING_ACADEMIC_YEAR_OFFSET = 1
#: Contract ``parameters``; the build refuses a contract whose block differs (the code never silently keeps old values).
CONTRACT_PARAMETERS = {
    "forward_match_days": FORWARD_MATCH_DAYS, "cfbd_local_offset_hours": list(CFBD_LOCAL_OFFSET_HOURS),
    "same_pair_same_score_window_days": SAME_PAIR_WINDOW_DAYS, "spring_2020_from": SPRING_2020_FROM,
    "binding_thresholds": BINDING_THRESHOLDS, "team_history_label_map": E2_LABEL_MAP,
    "team_history_label_codes": E2_LABEL_TO_CODE, "ranking_link_academic_year_offset": RANKING_ACADEMIC_YEAR_OFFSET,
    "contest_status_vocabulary": list(CONTEST_STATUSES), "single_source_exposure": EXPOSURE_2024_2025,
}


class PopulationRefused(ValueError):
    """A refusal with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# ---------------------------------------------------------------------------------------------- canonical bytes

def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_hash(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_instant(value: str) -> datetime:
    """A timezone-aware instant; naive or malformed values are refused (never compared as strings)."""
    try:
        instant = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise PopulationRefused("INVALID_INSTANT", f"{value!r} is not an ISO-8601 instant") from exc
    if instant.utcoffset() is None:
        raise PopulationRefused("NAIVE_INSTANT", f"{value!r} carries no UTC offset")
    return instant.astimezone(timezone.utc)


# ---------------------------------------------------------------------------------------------- contract

def load_contract(path: Path) -> tuple[dict[str, Any], str]:
    """Load and validate the population contract; the builder refuses to run without it."""
    contract_path = Path(path)
    if not contract_path.is_file():
        raise PopulationRefused("CONTRACT_MISSING", f"no contract at {contract_path}")
    raw = contract_path.read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    validate_contract(contract)
    return contract, sha256_bytes(raw)


def validate_contract(contract: dict[str, Any]) -> None:
    """Refuse contracts that change the delivered tranche, prove code 3, or let observations define denominators."""
    seasons = contract.get("delivery_seasons")
    if seasons != list(DELIVERY_SEASONS):
        raise PopulationRefused("CONTRACT_SEASONS_INVALID",
                                f"delivery seasons must be exactly 2016-2025, got {seasons!r}")
    table = (contract.get("division_decoding") or {}).get("table") or {}
    for code, label in (("11", "FBS"), ("12", "FCS"), ("2", "DII"), ("3", "OUTSIDE_DI_CODE_3")):
        if (table.get(code) or {}).get("label") != label:
            raise PopulationRefused("CONTRACT_DECODING_INVALID", f"code {code} must decode to {label}")
    code3 = table.get("3") or {}
    if code3.get("proof_state") != "INFERRED_UNPROVEN" or "III" in str(code3.get("label", "")).upper():
        raise PopulationRefused("CONTRACT_CODE3_PROVEN", "code 3 must stay OUTSIDE_DI_CODE_3 with an unproven inference")
    if set(table) != {"11", "12", "2", "3"}:
        raise PopulationRefused("CONTRACT_DECODING_INVALID", f"unexpected decoding table codes {sorted(table)}")
    regex = (contract.get("division_decoding") or {}).get("accepted_forms_regex")
    if regex != CODE_FORM_RE.pattern:
        raise PopulationRefused("CONTRACT_CODE_FORMS_INVALID", f"accepted code forms must be {CODE_FORM_RE.pattern}")
    denominator = contract.get("denominator_authority") or {}
    if (denominator.get("rule") != "UNION_OF_EXPECTED_KEYS_E1_TO_E6"
            or denominator.get("observed_rows_define_denominator") is not False
            or denominator.get("cfbd_rows_define_denominator") is not False):
        raise PopulationRefused("CONTRACT_DENOMINATOR_FROM_OBSERVATIONS",
                                "the denominator must be the E1-E6 expected-key union, never observed or CFBD rows")
    if set(contract.get("observation_only_sources") or []) != {"E3", "E5", "E6"}:
        raise PopulationRefused("CONTRACT_AUTHORITY_INVALID", "E3, E5 and E6 must stay observation-only")
    recon = contract.get("reconciliation") or {}
    if recon.get("two_source_seasons") != list(TWO_SOURCE_SEASONS) or recon.get("single_source_seasons") != list(
            SINGLE_SOURCE_SEASONS):
        raise PopulationRefused("CONTRACT_RECONCILIATION_SCOPE_INVALID",
                                "two-source reconciliation is 2016-2023 and 2024-2025 stays single-source")
    if recon.get("single_source_state") != SINGLE_SOURCE or recon.get("single_source_pass_or_verified") != "REFUSED":
        raise PopulationRefused("CONTRACT_SINGLE_SOURCE_INVALID", "2024-2025 must stay SINGLE_SOURCE_UNRECONCILED")
    if contract.get("historical_audit_unit") != "HT38-NATIONAL-DI-CONTEST-2016-2025":
        raise PopulationRefused("CONTRACT_AUDIT_UNIT_INVALID", "unexpected historical audit unit")
    if contract.get("parameters") != CONTRACT_PARAMETERS:
        raise PopulationRefused("CONTRACT_PARAMETERS_MISMATCH",
                                "the contract parameter block differs from the values this producer implements")
    if (contract.get("contest_grain") or {}).get("contest_status_vocabulary") != list(CONTEST_STATUSES):
        raise PopulationRefused("CONTRACT_PARAMETERS_MISMATCH", "contest status vocabulary differs")


# ---------------------------------------------------------------------------------------------- outputs

def gzip_jsonl_bytes(header: dict[str, Any], rows: Iterable[dict[str, Any]]) -> bytes:
    """Deterministic gzip of a JSONL file whose first line is a header carrying the contract sha256."""
    text = io.StringIO()
    text.write(json.dumps({"_header": header}, sort_keys=True, ensure_ascii=False) + "\n")
    for row in rows:
        text.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=6) as handle:
        handle.write(text.getvalue().encode("utf-8"))
    return buffer.getvalue()


def read_gzip_jsonl(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        lines = [json.loads(line) for line in handle if line.strip()]
    if not lines or "_header" not in lines[0]:
        raise PopulationRefused("OUTPUT_HEADER_MISSING", f"{path} has no header line")
    return lines[0]["_header"], lines[1:]


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def identity_document(*, stage: str, contract_sha256: str, inputs: dict[str, Any], upstream: dict[str, Any],
                      outputs: dict[str, str]) -> dict[str, Any]:
    if stage not in STAGES:
        raise PopulationRefused("UNKNOWN_STAGE", stage)
    return {"schema": SCHEMA_VERSION, "population": POPULATION, "stage": stage, "contract_sha256": contract_sha256,
            "producer": PRODUCER_VERSION, "inputs": inputs, "upstream": upstream, "outputs": dict(sorted(outputs.items()))}


def runtime_versions() -> dict[str, str]:
    """Recorded in run manifests (outside the identity): output bytes are reproducible on this runtime."""
    import platform
    import sys
    import zlib
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "zlib": zlib.ZLIB_RUNTIME_VERSION, "sqlite": sqlite3.sqlite_version}


def materialize(*, canonical_root: Path, manifest_root: Path, stage: str, contract_sha256: str,
                inputs: dict[str, Any], upstream: dict[str, Any], files: dict[str, bytes],
                manifest_extra: dict[str, Any]) -> dict[str, Any]:
    """Write one content-addressed stage root, create-only.

    The identity is the SHA-256 of the canonical identity document, which names every output file's SHA-256. Data
    files are written into a temporary sibling and renamed into place, so a root never holds a partial file set. An
    existing identity whose files hold exactly the same names and bytes is verified and left untouched; anything else
    is refused as an immutable collision. A verified root without its run manifest gets the manifest written once.
    """
    outputs = {name: sha256_bytes(payload) for name, payload in sorted(files.items())}
    document = identity_document(stage=stage, contract_sha256=contract_sha256, inputs=inputs, upstream=upstream,
                                 outputs=outputs)
    identity = stable_hash(document)
    data_dir = Path(canonical_root) / "sha256" / identity
    manifest_dir = Path(manifest_root) / "sha256" / identity
    manifest_path = manifest_dir / "run_manifest.json"
    written = 0
    if data_dir.exists():
        present = sorted(p.name for p in data_dir.iterdir())
        if present != sorted(files):
            raise PopulationRefused("IMMUTABLE_COLLISION", f"{data_dir} holds {present}, expected {sorted(files)}")
        for name, payload in files.items():
            if (data_dir / name).read_bytes() != payload:
                raise PopulationRefused("IMMUTABLE_COLLISION", f"{data_dir / name} exists with different bytes")
        state = "ALREADY_PRESENT_IDENTICAL"
    elif manifest_dir.exists():
        raise PopulationRefused("IMMUTABLE_COLLISION", f"{manifest_dir} exists without its data root")
    else:
        partial = data_dir.parent / f".partial-{identity}-{os.getpid()}"
        partial.mkdir(parents=True, exist_ok=False)
        for name, payload in sorted(files.items()):
            with (partial / name).open("xb") as handle:
                handle.write(payload)
            written += len(payload)
        os.rename(partial, data_dir)
        state = "MATERIALIZED"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("identity_document") != document or existing.get("identity") != identity:
            raise PopulationRefused("IMMUTABLE_COLLISION", f"{manifest_path} binds a different identity document")
    else:
        manifest = {"identity": identity, "identity_document": document, **manifest_extra, "runtime": runtime_versions()}
        manifest_dir.mkdir(parents=True, exist_ok=True)
        payload = json_bytes(manifest)
        with manifest_path.open("xb") as handle:
            handle.write(payload)
        written += len(payload)
        if state == "ALREADY_PRESENT_IDENTICAL":
            state = "MANIFEST_COMPLETED"
    return {"identity": identity, "state": state, "data_dir": str(data_dir), "manifest": str(manifest_path),
            "identity_document": document, "written_bytes": written}


def load_stage_manifest(path: Path, *, stage: str, contract_sha256: str) -> dict[str, Any]:
    """Read and verify an upstream stage manifest (identity, stage, contract, every output byte)."""
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise PopulationRefused("UPSTREAM_MANIFEST_MISSING", str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    document = manifest.get("identity_document") or {}
    identity = stable_hash(document)
    if identity != manifest.get("identity") or identity != manifest_path.parent.name:
        raise PopulationRefused("UPSTREAM_IDENTITY_MISMATCH", f"{manifest_path} does not hash to its directory")
    if document.get("stage") != stage:
        raise PopulationRefused("UPSTREAM_STAGE_MISMATCH", f"expected {stage}, found {document.get('stage')}")
    if document.get("contract_sha256") != contract_sha256:
        raise PopulationRefused("CONTRACT_IDENTITY_MISMATCH", "the upstream manifest was built under another contract")
    population_root = manifest_path.parent.parent.parent
    data_dir = population_root.parent.parent / "canonical" / population_root.name / "sha256" / identity
    for name, expected in (document.get("outputs") or {}).items():
        target = data_dir / name
        if not target.is_file() or sha256_file(target) != expected:
            raise PopulationRefused("UPSTREAM_OUTPUT_TAMPERED", f"{target} does not hash to {expected}")
    return {"identity": identity, "manifest": manifest, "data_dir": data_dir}


# ---------------------------------------------------------------------------------------------- page parsing

_HISTORY_ORG_RE = re.compile(r"/teams/history/MFB/(\d+)")
_CARD_HEADER_RE = re.compile(r'<div class="card-header">(.*?)</div>', re.DOTALL)
_LOGO_RE = re.compile(r'<img\b[^>]*?\balt="([^"]*)"[^>]*?All_Logos/sm//(\d+)\.gif', re.DOTALL)
_TAG_RE = re.compile(r"(?s)<[^>]+>")
_HEADER_RECORD_RE = re.compile(r"^(?P<name>.*?)\s*\((?P<w>\d+)-(?P<l>\d+)(?:-(?P<t>\d+))?\)\s*(?P<note>\*.*)?$", re.DOTALL)
_YEAR_SELECT_RE = re.compile(r'<select\b[^>]*\bid="year_list"[^>]*>(.*?)</select>', re.DOTALL)
_OPTION_RE = re.compile(r"<option\b([^>]*)>([^<]*)</option>", re.DOTALL)
_VALUE_RE = re.compile(r'\bvalue="(\d+)"')
_RANKING_HREF_RE = re.compile(r'href="(/rankings/[^"]*)"')
_DIVISION_PARAM_RE = re.compile(r"(?:\?|&)division=([^&#]*)")
_ORG_PARAM_RE = re.compile(r"(?:\?|&)org_id=([^&#]*)")
_YEAR_PARAM_RE = re.compile(r"(?:\?|&)academic_year=([^&#]*)")
_SCHEDULE_CARD_RE = re.compile(r'<div class="card-header">\s*Schedule/Results\s*</div>(.*?)</table>', re.DOTALL)
_SCHEDULE_ROW_RE = re.compile(r'<tr class="underline_rows">(.*?)</tr>', re.DOTALL)
_TD_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.DOTALL)
_DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_TEAM_LINK_RE = re.compile(r'<a\b[^>]*href="/teams/(\d+)"')
_CONTEST_LINK_RE = re.compile(r'<a\b[^>]*href="/contests/(\d+)/box_score"[^>]*>(.*?)</a>(\s*\*)?', re.DOTALL)
_SCORE_RE = re.compile(r"^([WLT])\s*(\d+)\s*-\s*(\d+)\s*(?:\((-?\d+)\s*OT\))?")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RANK_PREFIX_RE = re.compile(r"^#\s*\d+\s+")
_EVENT_SUFFIX_RE = re.compile(r"^(?P<site>[^()]*?)\s*(?:\((?P<event>[^()]*)\))?\s*$")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub(" ", fragment))).strip()


def season_label(season: int) -> str:
    return f"{season}-{(season + 1) % 100:02d}"


def _canonical_number(value: str) -> str:
    value = value.strip()
    return value[:-2] if CODE_FORM_RE.match(value) and value.endswith(".0") else value


def page_division_codes(page: dict[str, Any], season: int) -> tuple[list[str], int]:
    """Codes from ranking links bound to the page's own organization and academic year (season + 1).

    Returns the bound codes and the number of ranking links that name another organization or year (or neither)."""
    year = str(season + RANKING_ACADEMIC_YEAR_OFFSET)
    codes: list[str] = []
    mismatched = 0
    for link in page.get("ranking_links", []):
        if link["org_id"] is not None and link["org_id"] == page.get("org_id") and link["academic_year"] == year:
            codes.extend(link["codes"])
        elif link["codes"]:
            mismatched += 1
    return codes, mismatched


def decode_division(raw_codes: list[str], table: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize ``N``/``N.0`` forms and map exactly one distinct code through the contract table."""
    if not raw_codes:
        return {"decode_state": "NO_CODE", "code": None, "label": None, "raw_codes": []}
    canonical = set()
    for raw in raw_codes:
        if not CODE_FORM_RE.match(raw):
            return {"decode_state": "MALFORMED_CODE", "code": None, "label": None, "raw_codes": sorted(set(raw_codes))}
        canonical.add(raw[:-2] if raw.endswith(".0") else raw)
    if len(canonical) != 1:
        return {"decode_state": "MULTIPLE_CODES", "code": None, "label": None, "raw_codes": sorted(set(raw_codes))}
    code = canonical.pop()
    if code not in table:
        return {"decode_state": "UNKNOWN_CODE", "code": code, "label": None, "raw_codes": sorted(set(raw_codes))}
    return {"decode_state": "DECODED", "code": code, "label": table[code]["label"], "raw_codes": sorted(set(raw_codes))}


def _parse_opponent(cell: str) -> dict[str, Any]:
    parts = _BR_RE.split(cell, maxsplit=1)
    head = parts[0]
    suffix = _text(parts[1]) if len(parts) > 1 else ""
    head_text = _text(head)
    away = head_text.startswith("@")
    link = _TEAM_LINK_RE.search(head)
    logo = _LOGO_RE.search(head)
    if logo is not None:
        name = html.unescape(logo.group(1)).strip()
    else:
        name = head_text[1:].strip() if away else head_text
        name = _RANK_PREFIX_RE.sub("", name).strip()
    neutral_site, event = None, None
    if suffix:
        if suffix.startswith("@"):
            matched = _EVENT_SUFFIX_RE.match(suffix[1:].strip())
            neutral_site = (matched.group("site") if matched else suffix[1:]).strip() or None
            event = matched.group("event").strip() if matched and matched.group("event") else None
        else:
            event = suffix
    return {"opponent_team_season_id": link.group(1) if link else None,
            "opponent_logo_org_id": logo.group(2) if logo else None,
            "opponent_name": name or None, "opponent_linked": link is not None,
            "page_team_marked_away": away, "neutral_site": neutral_site, "event_label": event}


def _parse_result(cell: str) -> dict[str, Any]:
    link = _CONTEST_LINK_RE.search(cell)
    flags: list[str] = []
    text = _text(link.group(2)) if link else _text(cell)
    contest_id = link.group(1) if link else None
    if link and link.group(3) and "*" in link.group(3):
        flags.append("EXEMPTED_NOT_COUNTED")
    elif not link and text.endswith("*"):
        flags.append("EXEMPTED_NOT_COUNTED")
        text = text[:-1].strip()
    score = _SCORE_RE.match(text)
    result: dict[str, Any] = {"ncaa_contest_id": contest_id, "result_text": text, "result_letter": None,
                              "team_points": None, "opponent_points": None, "overtime_marker": None}
    if score:
        letter, mine, theirs, overtime = score.group(1), int(score.group(2)), int(score.group(3)), score.group(4)
        result.update(result_letter=letter, team_points=mine, opponent_points=theirs, status="COMPLETED",
                      overtime_marker=int(overtime) if overtime is not None else None)
        if overtime is not None and int(overtime) < 0:
            flags.append("NEGATIVE_OVERTIME_MARKER")
        expected = "W" if mine > theirs else ("L" if mine < theirs else "T")
        if letter != expected:
            flags.append("RESULT_LETTER_CONTRADICTS_SCORE")
    # Forfeit and no-contest text anywhere in the cell outranks a stated score: the score stays an observation and
    # the row is never competitive (contract contest_grain.status_mapping).
    whole = _text(cell).lower()
    if "forfeit" in whole:
        result["status"] = "FORFEIT"
    elif "no contest" in whole:
        result["status"] = "NO_CONTEST"
    elif not score:
        result["status"] = "CANCELED" if "cancel" in text.lower() else "UNSCORED"
    if contest_id is None:
        flags.append("NO_CONTEST_LINK")
    result["flags"] = flags
    return result


def parse_graph_page(payload: str) -> dict[str, Any]:
    """Parse one NCAA team-season page: identity, header record, season selector, division codes, schedule rows.

    The record comes from the target team-season's header card only (never from the season selector or the
    school-sports navigation, which lists entries like '2026-27 Football (0-0)'). Division codes come from the
    page's own ranking links. Schedule rows come from the Schedule/Results table only.
    """
    orgs = sorted(set(_HISTORY_ORG_RE.findall(payload)))
    page: dict[str, Any] = {"org_id": orgs[0] if len(orgs) == 1 else None, "org_ids_seen": orgs,
                            "flags": [] if len(orgs) == 1 else ["ORG_ID_NOT_UNIQUE"]}
    header = None
    for block in _CARD_HEADER_RE.findall(payload):
        text = _text(block)
        matched = _HEADER_RECORD_RE.match(text)
        if matched:
            header = (block, matched)
            break
    if header is None:
        page.update(team_name=None, team_name_source=None, header_record=None, header_note=None)
        page["flags"].append("HEADER_RECORD_UNPARSED")
    else:
        block, matched = header
        logo = _LOGO_RE.search(block)
        wins, losses, ties = int(matched.group("w")), int(matched.group("l")), matched.group("t")
        page.update(team_name=html.unescape(logo.group(1)).strip() if logo else matched.group("name").strip(),
                    team_name_source="HEADER_LOGO_ALT" if logo else "HEADER_TEXT",
                    header_logo_org_id=logo.group(2) if logo else None,
                    header_record={"wins": wins, "losses": losses, "ties": int(ties) if ties is not None else None,
                                   "text": f"{wins}-{losses}" + (f"-{ties}" if ties is not None else "")},
                    header_note=(matched.group("note") or None))
    options: dict[str, str] = {}
    selected = None
    select = _YEAR_SELECT_RE.search(payload)
    if select:
        for attrs, label in _OPTION_RE.findall(select.group(1)):
            value = _VALUE_RE.search(attrs)
            if not value:
                continue
            options[label.strip()] = value.group(1)
            if "selected" in attrs:
                selected = (label.strip(), value.group(1))
    page["season_options"] = options
    page["selected_season_label"], page["selected_team_season_id"] = selected if selected else (None, None)
    raw_codes: list[str] = []
    links: list[dict[str, Any]] = []
    for href in _RANKING_HREF_RE.findall(payload):
        query = html.unescape(href)
        codes = _DIVISION_PARAM_RE.findall(query)
        raw_codes.extend(codes)
        org_param = _ORG_PARAM_RE.search(query)
        year_param = _YEAR_PARAM_RE.search(query)
        links.append({"codes": codes, "org_id": _canonical_number(org_param.group(1)) if org_param else None,
                      "academic_year": _canonical_number(year_param.group(1)) if year_param else None})
    page["raw_division_codes"] = raw_codes
    page["ranking_links"] = links
    schedule = _SCHEDULE_CARD_RE.search(payload)
    rows: list[dict[str, Any]] = []
    if schedule is None:
        page["flags"].append("SCHEDULE_TABLE_MISSING")
    else:
        for index, row_html in enumerate(_SCHEDULE_ROW_RE.findall(schedule.group(1))):
            cells = _TD_RE.findall(row_html)
            if len(cells) < 3:
                continue
            date_text = _text(cells[0])
            date_match = _DATE_RE.search(date_text)
            row = {"row_index": index, "date_text": date_text,
                   "date": (f"{date_match.group(3)}-{date_match.group(1)}-{date_match.group(2)}" if date_match else None),
                   **_parse_opponent(cells[1]), **_parse_result(cells[2]),
                   "attendance_text": _text(cells[3]) if len(cells) > 3 else None}
            if date_match and date_text != date_match.group(0):
                row["flags"] = row["flags"] + ["DATE_WITH_TIME"]
            if date_match is None:
                row["flags"] = row["flags"] + ["DATE_UNPARSED"]
            rows.append(row)
    page["schedule_rows"] = rows
    return page


# ---------------------------------------------------------------------------------------------- team history (E2)

_HISTORY_TABLE_RE = re.compile(r'<table\b[^>]*\bid="team_history_data_table"[^>]*>(.*?)</table>', re.DOTALL)
_TBODY_RE = re.compile(r"<tbody\b[^>]*>(.*?)</tbody>", re.DOTALL)
_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
_ORG_HIDDEN_RE = re.compile(r'<input\b[^>]*\bid="org_id_search"[^>]*\bvalue="(\d+)"|<input\b[^>]*\bvalue="(\d+)"[^>]*\bid="org_id_search"')
_ORG_SELECT_RE = re.compile(r'<select\b[^>]*\bid="org_id_select"[^>]*>(.*?)</select>', re.DOTALL)
_YEAR_LABEL_RE = re.compile(r"^(\d{4})-(\d{2})$")


def parse_team_history_page(payload: str) -> dict[str, Any] | None:
    """One official Year-By-Year History page; rows with 7+ cells kept, including blank 2020 records."""
    table = _HISTORY_TABLE_RE.search(payload)
    if table is None:
        return None
    org = _ORG_HIDDEN_RE.search(payload)
    org_id = (org.group(1) or org.group(2)) if org else None
    name = None
    select = _ORG_SELECT_RE.search(payload)
    if select:
        for attrs, label in _OPTION_RE.findall(select.group(1)):
            value = _VALUE_RE.search(attrs)
            if value and "selected" in attrs and value.group(1) == org_id:
                name = html.unescape(label).strip()
    body = _TBODY_RE.search(table.group(1))
    rows = []
    for row_html in _ROW_RE.findall(body.group(1) if body else table.group(1)):
        cells_html = _TD_RE.findall(row_html)
        if len(cells_html) < 7:
            continue
        cells = [_text(c) for c in cells_html]
        label = _YEAR_LABEL_RE.match(cells[0])
        if not label:
            continue
        link = _TEAM_LINK_RE.search(cells_html[0])
        record = []
        for value in cells[4:7]:
            record.append(int(value) if value.isdigit() else None)
        played = all(v is not None for v in record[:2])
        rows.append({"season": int(label.group(1)), "season_label": cells[0],
                     "team_season_id": link.group(1) if link else None, "division_label": cells[2] or None,
                     "conference": cells[3] or None, "wins": record[0], "losses": record[1], "ties": record[2],
                     "record_state": "PLAYED" if played else "UNPLAYED_OR_BLANK",
                     "notes": cells[8] if len(cells) > 8 else None})
    return {"org_id": org_id, "team_name": name, "rows": rows}


# ---------------------------------------------------------------------------------------------- manifests (E1)

def read_manifest(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    document = json.loads(raw.decode("utf-8"))
    captures = document.get("captures") or []
    return {"path": str(path), "directory_identity": Path(path).parent.name, "sha256": sha256_bytes(raw),
            "state": document.get("state"), "issued_at_utc": document.get("issued_at_utc"),
            "discovery_identity": document.get("discovery_identity"), "season": document.get("season"),
            "captures": captures, "failures": document.get("failures") or [],
            "discovered_team_season_ids": [str(x) for x in document.get("discovered_team_season_ids") or []],
            "capture_count": len(captures), "declared_capture_count": document.get("team_page_capture_count"),
            "pairs": sorted({(str(c.get("team_season_id")), c.get("raw_sha256")) for c in captures})}


def bind_season_manifests(manifests: list[dict[str, Any]], eligible_state: str = "COMPLETE_GRAPH_EXHAUSTED"
                          ) -> dict[str, Any]:
    """Apply the contract rule: most captures among COMPLETE manifests, latest issued_at_utc, else refuse."""
    census = []
    eligible = []
    for m in manifests:
        problems = []
        if m["discovery_identity"] != m["directory_identity"]:
            problems.append("DISCOVERY_IDENTITY_MISMATCH")
        if m["declared_capture_count"] is not None and m["declared_capture_count"] != m["capture_count"]:
            problems.append("CAPTURE_COUNT_MISMATCH")
        if m["state"] == eligible_state and not problems:
            eligible.append(m)
        census.append({"identity": m["directory_identity"], "sha256": m["sha256"], "state": m["state"],
                       "issued_at_utc": m["issued_at_utc"], "captures": m["capture_count"],
                       "failures": len(m["failures"]), "problems": problems})
    if not eligible:
        raise PopulationRefused("NO_ELIGIBLE_MANIFEST", "no COMPLETE_GRAPH_EXHAUSTED manifest with a valid identity")
    most = max(m["capture_count"] for m in eligible)
    top = [m for m in eligible if m["capture_count"] == most]
    if len(top) > 1:
        latest = max(parse_instant(m["issued_at_utc"]) for m in top)
        top = [m for m in top if parse_instant(m["issued_at_utc"]) == latest]
    if len(top) != 1:
        raise PopulationRefused("REFUSED_UNBREAKABLE_TIE", f"{len(top)} manifests tie on captures and issued_at_utc")
    bound = top[0]
    bound_pairs = set(bound["pairs"])
    for row, m in zip(census, manifests):
        if m is bound:
            row["relation"] = "BOUND"
            row["pairs_absent_from_bound"] = []
            continue
        pairs = set(m["pairs"])
        if pairs == bound_pairs:
            relation = "EQUAL"
        elif pairs <= bound_pairs:
            relation = "SUBSET"
        elif pairs >= bound_pairs:
            relation = "SUPERSET"
        elif pairs & bound_pairs:
            relation = "OVERLAP"
        else:
            relation = "DISJOINT"
        row["relation"] = relation
        row["pairs_absent_from_bound"] = sorted([list(p) for p in pairs - bound_pairs])
    return {"bound": bound, "census": census}


# ---------------------------------------------------------------------------------------------- names and CFBD

TOKEN_EXPANSIONS_DEFAULT = {"st": "state", "so": "southern"}


def normalize_name(value: str, expansions: dict[str, str]) -> str:
    folded = unicodedata.normalize("NFKD", html.unescape(str(value))).encode("ascii", "ignore").decode("ascii")
    folded = folded.lower().replace("&", " and ")
    return " ".join(expansions.get(token, token) for token in re.sub(r"[^a-z0-9]+", " ", folded).split())


def cfbd_local_dates(start: str | None) -> list[str]:
    """Candidate US-local calendar dates of a CFBD UTC instant (contract reconciliation.cfbd_date_basis)."""
    if not start:
        return []
    instant = parse_instant(start)
    return sorted({(instant + timedelta(hours=hours)).date().isoformat() for hours in CFBD_LOCAL_OFFSET_HOURS})


def cfbd_days(game: dict[str, Any], page_date: str | None) -> int | None:
    """Smallest day distance between an NCAA page date and a CFBD row's candidate local dates."""
    if not page_date or not game.get("local_dates"):
        return None
    return min(_days(local, page_date) for local in game["local_dates"])


def load_cfbd_games(path: Path, *, expected_sha256: str, route: str) -> list[dict[str, Any]]:
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise PopulationRefused("INPUT_HASH_MISMATCH", f"{path} does not hash to {expected_sha256}")
    rows = []
    for game in json.loads(raw.decode("utf-8")):
        start = game.get("startDate")
        rows.append({"cfbd_game_id": str(game["id"]), "season": game.get("season"), "season_type": game.get("seasonType"),
                     "week": game.get("week"), "start_utc": start, "local_dates": cfbd_local_dates(start),
                     "completed": game.get("completed"), "neutral_site": game.get("neutralSite"),
                     "home_id": str(game["homeId"]) if game.get("homeId") is not None else None,
                     "home_team": game.get("homeTeam"), "home_classification": game.get("homeClassification"),
                     "home_points": game.get("homePoints"),
                     "away_id": str(game["awayId"]) if game.get("awayId") is not None else None,
                     "away_team": game.get("awayTeam"), "away_classification": game.get("awayClassification"),
                     "away_points": game.get("awayPoints"), "route": route})
    return rows


def union_cfbd(routes: list[list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicate by CFBD game id; identical duplicate rows merge their routes, differing rows are conflicts."""
    merged: dict[str, dict[str, Any]] = {}
    conflicts = []
    for rows in routes:
        for row in rows:
            key = row["cfbd_game_id"]
            if key not in merged:
                merged[key] = {**row, "routes": [row["route"]]}
                continue
            current = merged[key]
            same = all(current.get(k) == row.get(k) for k in row if k != "route")
            if same:
                current["routes"] = sorted(set(current["routes"]) | {row["route"]})
            else:
                conflicts.append({"cfbd_game_id": key, "routes": [current["routes"], row["route"]]})
                current["route_conflict"] = True
    return [merged[k] for k in sorted(merged, key=int)], conflicts


def load_registry(path: Path, *, expected_sha256: str) -> dict[str, Any]:
    if sha256_file(path) != expected_sha256:
        raise PopulationRefused("INPUT_HASH_MISMATCH", f"{path} does not hash to {expected_sha256}")
    cfbd_to_canonical: dict[str, str] = {}
    aliases: dict[str, set[str]] = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("entity_type") != "team":
                continue
            if row.get("record_type") == "ENTITY" and (row.get("identity_key") or "").startswith("TEAM|SRC-002|"):
                cfbd_to_canonical[row["identity_key"].split("|", 2)[2]] = row["canonical_id"]
            elif (row.get("record_type") == "ALIAS" and row.get("resolution_state") == "AUTO_ACCEPTED_VERIFIED"
                  and row.get("alias")):
                start = (row.get("effective_from") or "0000")[:4]
                end = (row.get("effective_to_exclusive") or "9999")[:4]
                if start <= "2025" and end > "2016":
                    aliases.setdefault(row["canonical_id"], set()).add(row["alias"])
    return {"cfbd_to_canonical": cfbd_to_canonical, "canonical_aliases": aliases}


def bind_organizations(org_games: dict[str, list[tuple[str, int, int]]], org_names: dict[str, set[str]],
                       cfbd_games: list[dict[str, Any]], cfbd_names: dict[str, set[str]],
                       expansions: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Bind NCAA organizations to CFBD team ids: name candidates confirmed by each team's own schedule fingerprint.

    ``org_games`` holds each organization's completed, scored 2016-2023 games in the CFBD-covered scope as
    (date, own points, opponent points). Name-only bindings are never accepted.
    """
    t = BINDING_THRESHOLDS
    index: dict[tuple[str, int, int], set[str]] = {}
    for game in cfbd_games:
        if game["home_points"] is None or game["away_points"] is None or not game["local_dates"]:
            continue
        for team, own, other in ((game["home_id"], game["home_points"], game["away_points"]),
                                 (game["away_id"], game["away_points"], game["home_points"])):
            if team is None:
                continue
            for local in game["local_dates"]:
                index.setdefault((local, int(own), int(other)), set()).add(team)
    name_index: dict[str, set[str]] = {}
    for team, names in cfbd_names.items():
        for name in names:
            name_index.setdefault(normalize_name(name, expansions), set()).add(team)
    results: dict[str, dict[str, Any]] = {}
    for org, games in org_games.items():
        counts: dict[str, int] = {}
        for game_date, own, other in games:
            day = date.fromisoformat(game_date)
            teams: set[str] = set()
            for delta in range(-FORWARD_MATCH_DAYS, FORWARD_MATCH_DAYS + 1):
                teams |= index.get((date.fromordinal(day.toordinal() + delta).isoformat(), own, other), set())
            for team in teams:
                counts[team] = counts.get(team, 0) + 1
        n = len(games)
        candidates = sorted({t for name in org_names.get(org, set())
                             for t in name_index.get(normalize_name(name, expansions), set())})
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        best_team, best = ranked[0] if ranked else (None, 0)
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        strict_max = best > runner_up
        rule, team = None, None
        if n == 0:
            reason = "NO_SCHEDULE_EVIDENCE"
        elif len(candidates) == 1:
            c = candidates[0]
            fc = counts.get(c, 0)
            if (fc >= t["name_confirmed_min_games"] and fc >= t["name_confirmed_min_share"] * n and best_team == c
                    and strict_max):
                rule, team = "NAME_CONFIRMED_BY_SCHEDULE", c
                reason = None
            else:
                reason = "NAME_CANDIDATE_NOT_CONFIRMED_BY_SCHEDULE"
        elif len(candidates) > 1:
            qualified = [c for c in candidates if counts.get(c, 0) >= t["name_confirmed_min_games"]
                         and counts.get(c, 0) >= t["name_confirmed_min_share"] * n]
            others_low = all(counts.get(c, 0) < t["collision_other_max_share"] * n for c in candidates if c not in qualified)
            if len(qualified) == 1 and others_low and best_team == qualified[0] and strict_max:
                rule, team = "NAME_COLLISION_DISAMBIGUATED_BY_SCHEDULE", qualified[0]
                reason = None
            else:
                reason = "NAME_COLLISION_NOT_DISAMBIGUATED"
        else:
            if (best_team is not None and best >= t["fingerprint_only_min_games"]
                    and best >= t["fingerprint_only_min_share"] * n
                    and runner_up <= t["fingerprint_only_runner_up_max_share"] * n):
                rule, team = "SCHEDULE_FINGERPRINT_ONLY", best_team
                reason = None
            else:
                reason = "NO_NAME_CANDIDATE_AND_FINGERPRINT_BELOW_THRESHOLD"
        results[org] = {"org_id": org, "cfbd_team_id": team, "rule": rule, "reason": reason, "n_games": n,
                        "name_candidates": candidates, "best_fingerprint": [best_team, best],
                        "runner_up_fingerprint": runner_up, "candidate_fingerprints":
                        {c: counts.get(c, 0) for c in candidates}}
    by_team: dict[str, list[str]] = {}
    for org, result in results.items():
        if result["cfbd_team_id"]:
            by_team.setdefault(result["cfbd_team_id"], []).append(org)
    for team, orgs in by_team.items():
        if len(orgs) > 1:
            for org in orgs:
                results[org].update(cfbd_team_id=None, rule=None, reason="BINDING_NOT_ONE_TO_ONE",
                                    competing_orgs=sorted(orgs))
    return results


# ---------------------------------------------------------------------------------------------- M1: program-season

DISCOVERY_REL = "manifests/acquisition/BAT-554-NCAA-OFFICIAL-BOUNDED-V1/discovery"
SRC015_REL = "raw/SRC-015/ncaa_team_season_discovery"
TEAM_HISTORY_REL = "raw/SRC-NCAA-OFFICIAL-STATS/ncaa_official_team_history"
FCS_ROUTE_REL = "ops/cycle30_work/raw/games"
SRC002_REL = "raw/SRC-002/games"


def season_manifests(data_root: Path, season: int) -> list[dict[str, Any]]:
    base = Path(data_root) / DISCOVERY_REL / str(season) / "sha256"
    if not base.is_dir():
        return []
    return [read_manifest(d / "ncaa_team_graph_discovery_manifest.json") for d in sorted(base.iterdir())
            if (d / "ncaa_team_graph_discovery_manifest.json").is_file()]


def _key(org: str | None, ts: str | None, season: int) -> str:
    return f"org:{org}:{season}" if org else f"ts:{ts}:{season}"


def bat554_crosscheck(text: str, team_season_id: str, raw_sha256: str, page: dict[str, Any]) -> dict[str, Any]:
    """Read-only reuse of the BAT-554 public parser: its scored rows must be a subset of this parse.

    ``ncaa_contest_reconciliation.parse_team_page`` keeps only box-score rows with a linked opponent and reports no
    neutral site, so it can only confirm a subset (contest id, own points, opponent points, away marker).
    """
    owner, rows = ncaa_contest_reconciliation.parse_team_page(text, team_season_id=team_season_id, raw_sha256=raw_sha256)
    theirs = {(r["contest_id"], r["source_team_points"], r["opponent_points"], r["source_team_is_away"]) for r in rows}
    mine = {(r["ncaa_contest_id"], r["team_points"], r["opponent_points"], r["page_team_marked_away"])
            for r in page.get("schedule_rows", []) if r.get("ncaa_contest_id")}
    org_agrees = owner is None or owner.get("source_team_org_id") == page.get("org_id")
    return {"state": "SUBSET" if theirs <= mine and org_agrees else "DISAGREES", "bat554_rows": len(theirs),
            "rows_here": len(mine), "missing_here": sorted(map(list, theirs - mine))[:5], "org_agrees": org_agrees}


def verify_bound_against_contract(bound: dict[str, Any], declared: dict[str, Any], season: int) -> None:
    """The rule's result must equal the contract's declared identity, file sha256 and capture count."""
    if (bound["directory_identity"] != declared["identity"] or bound["sha256"] != declared["sha256"]
            or bound["capture_count"] != declared["captures"]):
        raise PopulationRefused("INPUT_BINDING_MISMATCH", f"season {season} binds {bound['directory_identity']} "
                                f"({bound['sha256']}, {bound['capture_count']} captures)")


def classify_absent_pairs(binding: dict[str, Any], manifests: list[dict[str, Any]], data_root: Path,
                          season: int) -> None:
    """Rehash and identify every superseded pair absent from the bound manifest; each stays an explicit CONFLICT row."""
    by_identity = {m["directory_identity"]: m for m in manifests}
    for row in binding["census"]:
        classified = []
        manifest = by_identity.get(row["identity"])
        captures = {(str(c.get("team_season_id")), c.get("raw_sha256")): c for c in (manifest or {}).get("captures", [])}
        for ts, raw_sha in row.get("pairs_absent_from_bound", []):
            capture = captures.get((ts, raw_sha)) or {}
            raw_path = Path(data_root) / Path(*str(capture.get("raw_relative_path", "")).split("/"))
            payload = raw_path.read_bytes() if capture and raw_path.is_file() else None
            rehash_ok = payload is not None and sha256_bytes(payload) == raw_sha
            entry: dict[str, Any] = {"team_season_id": ts, "raw_sha256": raw_sha, "rehash_ok": rehash_ok,
                                     "state": "CONFLICT"}
            if rehash_ok:
                page = parse_graph_page(payload.decode("utf-8", errors="replace"))
                entry.update(page_org_id=page.get("org_id"), page_team_name=page.get("team_name"),
                             page_season_label=page.get("selected_season_label"),
                             page_team_season_id=page.get("selected_team_season_id"))
                in_season = page.get("selected_season_label") == season_label(season)
                entry["page_team_season_id_matches_pair"] = page.get("selected_team_season_id") == ts
                entry["classification"] = ("IN_SEASON_TEAM_SEASON_ABSENT_FROM_BOUND" if in_season
                                           else "OUT_OF_SEASON_PAGE_IN_SUPERSEDED_MANIFEST")
            else:
                entry["classification"] = "UNVERIFIABLE_PAIR_PAYLOAD_MISSING"
            classified.append(entry)
        row["pairs_absent_classified"] = classified


def load_graph(contract: dict[str, Any], data_root: Path) -> dict[str, Any]:
    """Bind one manifest per season by the contract rule, verify it against the contract, rehash and parse pages."""
    data_root = Path(data_root)
    bindings = contract["input_bindings"]["bound_manifests"]
    table = contract["division_decoding"]["table"]
    seasons: dict[int, Any] = {}
    all_referenced: set[str] = set()
    for season_dir in sorted((data_root / DISCOVERY_REL).iterdir(), key=lambda p: p.name):
        if not season_dir.name.isdigit():
            continue
        for manifest_dir in sorted((season_dir / "sha256").iterdir()) if (season_dir / "sha256").is_dir() else []:
            path = manifest_dir / "ncaa_team_graph_discovery_manifest.json"
            if path.is_file():
                for capture in json.loads(path.read_text(encoding="utf-8")).get("captures") or []:
                    all_referenced.add(Path(capture.get("raw_relative_path", "")).name)
    for season in (2015, *DELIVERY_SEASONS):
        manifests = season_manifests(data_root, season)
        binding = bind_season_manifests(manifests)
        bound = binding["bound"]
        if season in DELIVERY_SEASONS:
            verify_bound_against_contract(bound, bindings[str(season)], season)
        pages: dict[str, dict[str, Any]] = {}
        for capture in bound["captures"]:
            ts = str(capture["team_season_id"])
            raw_path = data_root / Path(*capture["raw_relative_path"].split("/"))
            payload = raw_path.read_bytes() if raw_path.is_file() else None
            rehash_ok = payload is not None and sha256_bytes(payload) == capture["raw_sha256"] and \
                raw_path.name == f"{capture['raw_sha256']}.html"
            record: dict[str, Any] = {"season": season, "team_season_id": ts, "raw_relative_path":
                                      capture["raw_relative_path"], "raw_sha256": capture["raw_sha256"],
                                      "rehash_ok": rehash_ok, "link_schema": capture.get("link_schema"),
                                      "manifest_season_options": capture.get("season_options") or {}}
            if ts in pages:
                raise PopulationRefused("DUPLICATE_CAPTURE_IN_BOUND_MANIFEST",
                                        f"season {season} manifest captures team-season {ts} twice")
            if rehash_ok:
                text = payload.decode("utf-8", errors="replace")
                page = parse_graph_page(text)
                bound_codes, mismatched_links = page_division_codes(page, season)
                page["bound_division_codes"] = bound_codes
                page["ranking_links_identity_mismatched"] = mismatched_links
                if mismatched_links:
                    page["flags"].append("RANKING_LINK_IDENTITY_MISMATCH")
                page["decode"] = decode_division(bound_codes, table)
                page["bat554_parser_crosscheck"] = bat554_crosscheck(text, ts, capture["raw_sha256"], page)
                if page["bat554_parser_crosscheck"]["state"] != "SUBSET":
                    page["flags"].append("BAT554_PARSER_CROSSCHECK_DISAGREES")
                identity_ok = (page["selected_team_season_id"] == ts
                               and page["selected_season_label"] == season_label(season))
                if not identity_ok:
                    page["flags"].append("PAGE_IDENTITY_MISMATCH")
                record.update(page=page, identity_ok=identity_ok)
            pages[ts] = record
        if season in DELIVERY_SEASONS:
            accounted = set(pages) | {str(f["team_season_id"]) for f in bound["failures"]}
            missing = sorted(set(bound["discovered_team_season_ids"]) - accounted)
            if missing:
                raise PopulationRefused("DISCOVERED_ID_NOT_ACCOUNTED",
                                        f"season {season}: discovered ids neither captured nor failed: {missing[:10]}")
        classify_absent_pairs(binding, manifests, data_root, season)
        bound_paths = {Path(c["raw_relative_path"]).name for c in bound["captures"]}
        other_paths = {Path(c["raw_relative_path"]).name for m in manifests if m is not bound for c in m["captures"]}
        seasons[season] = {"binding": binding, "pages": pages,
                           "failures": {str(f["team_season_id"]): f for f in bound["failures"]},
                           "discovered": set(bound["discovered_team_season_ids"]),
                           "raw_only_in_non_bound": sorted(other_paths - bound_paths),
                           "captures_without_link_schema": sum(1 for c in bound["captures"] if "link_schema" not in c)}
    raw_dir = data_root / SRC015_REL
    raw_files = sorted(p.name for p in raw_dir.iterdir() if p.is_file())
    unreferenced = sorted(set(raw_files) - all_referenced)
    return {"seasons": seasons, "src015_file_count": len(raw_files), "src015_unreferenced": unreferenced}


def load_team_history(data_root: Path, expected_count: int) -> dict[str, Any]:
    root = Path(data_root) / TEAM_HISTORY_REL
    files = sorted(p for p in root.iterdir() if p.is_file())
    if len(files) != expected_count:
        raise PopulationRefused("INPUT_BINDING_MISMATCH", f"team-history file count {len(files)} != {expected_count}")
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    junk, variants = [], []
    names: dict[str, str] = {}
    for path in files:
        payload = path.read_bytes()
        parsed = parse_team_history_page(payload.decode("utf-8", errors="replace"))
        if parsed is None or not parsed["org_id"]:
            junk.append({"file": path.name, "bytes": len(payload), "sha256": sha256_bytes(payload)})
            continue
        if parsed["team_name"]:
            names[parsed["org_id"]] = parsed["team_name"]
        for row in parsed["rows"]:
            if row["season"] not in DELIVERY_SEASONS:
                continue
            key = (parsed["org_id"], row["season"])
            entry = {**row, "org_id": parsed["org_id"], "team_name": parsed["team_name"], "page_sha256": sha256_bytes(payload)}
            if key in by_key:
                old = {k: v for k, v in by_key[key].items() if k != "page_sha256"}
                new = {k: v for k, v in entry.items() if k != "page_sha256"}
                if old != new:
                    variants.append({"org_id": key[0], "season": key[1], "first": old, "second": new})
                    by_key[key]["variant_conflict"] = True
                continue
            by_key[key] = entry
    return {"rows": by_key, "junk_pages": junk, "variants": variants, "file_count": len(files), "names": names}


def load_cfbd_sources(contract: dict[str, Any], data_root: Path) -> dict[str, Any]:
    data_root = Path(data_root)
    ib = contract["input_bindings"]
    fbs = {}
    for season in DELIVERY_SEASONS:
        sha = ib["cfbd_fbs_route"][str(season)]
        fbs[season] = load_cfbd_games(data_root / SRC002_REL / f"sha256_{sha}.json", expected_sha256=sha, route="SRC-002")
    ledger_path = data_root / ib["cycle30_ledger"]["path"]
    if sha256_file(ledger_path) != ib["cycle30_ledger"]["sha256"]:
        raise PopulationRefused("INPUT_HASH_MISMATCH", "Cycle30 acquisition ledger")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    fcs = {}
    for season in TWO_SOURCE_SEASONS:
        binding = ib["cfbd_fcs_route"][str(season)]
        entries = [a for a in ledger.get("attempts") or [] if a.get("route") == "/games"
                   and (a.get("parameters") or {}) == {"classification": "fcs", "year": season}]
        if len(entries) != 1 or entries[0].get("raw_sha256") != binding["content_sha256"]:
            raise PopulationRefused("INPUT_BINDING_MISMATCH", f"Cycle30 ledger does not bind fcs {season}")
        rows = load_cfbd_games(data_root / FCS_ROUTE_REL / binding["file"], expected_sha256=binding["content_sha256"],
                               route="CYCLE30_FCS")
        if len(rows) != entries[0].get("row_count"):
            raise PopulationRefused("INPUT_BINDING_MISMATCH", f"Cycle30 fcs {season} row count")
        fcs[season] = rows
    membership_path = data_root / ib["cycle30_membership"]["path"]
    if sha256_file(membership_path) != ib["cycle30_membership"]["sha256"]:
        raise PopulationRefused("INPUT_HASH_MISMATCH", "Cycle30 membership")
    membership = [json.loads(line) for line in membership_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    registry = load_registry(data_root / ib["canonical_registry"]["path"], expected_sha256=ib["canonical_registry"]["sha256"])
    return {"fbs": fbs, "fcs": fcs, "membership": membership, "registry": registry}


def load_e6(repo_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    binding = contract["input_bindings"]["current_2026_population"]
    path = Path(repo_root) / binding["repository_path"]
    if sha256_file(path) != binding["sha256"]:
        raise PopulationRefused("INPUT_HASH_MISMATCH", "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION")
    return json.loads(path.read_text(encoding="utf-8"))


def _cfbd_id(program_id: str) -> str:
    return str(program_id).rsplit(":", 1)[-1]


def build_program_season(contract: dict[str, Any], data_root: Path, repo_root: Path) -> dict[str, Any]:
    """Assemble every expected program-season cell (E1-E6) with exactly one disposition."""
    graph = load_graph(contract, data_root)
    history = load_team_history(data_root, contract["input_bindings"]["team_history_root"]["file_count"])
    cfbd = load_cfbd_sources(contract, data_root)
    e6 = load_e6(repo_root, contract)
    expansions = contract["reconciliation"]["participant_resolution"]["token_expansions"]
    seasons = graph["seasons"]

    # team-season -> organization (pages), and adjacent-season season_options
    ts_org: dict[tuple[int, str], str] = {}
    code_of: dict[tuple[int, str], str | None] = {}
    for season, info in seasons.items():
        for ts, rec in info["pages"].items():
            page = rec.get("page")
            if page and page.get("org_id"):
                ts_org[(season, ts)] = page["org_id"]
                code_of[(season, page["org_id"])] = page["decode"]["code"] if page["decode"]["decode_state"] == "DECODED" else None
    # E4 and failed-capture organization recovery from adjacent seasons' selectors
    selector_org: dict[tuple[int, str], set[str]] = {}
    for season, info in seasons.items():
        for ts, rec in info["pages"].items():
            page = rec.get("page")
            if not page or not page.get("org_id"):
                continue
            for label, other_ts in page["season_options"].items():
                matched = _YEAR_LABEL_RE.match(label)
                if not matched:
                    continue
                other = int(matched.group(1))
                if other != season and other in DELIVERY_SEASONS and abs(other - season) == 1:
                    selector_org.setdefault((other, other_ts), set()).add(page["org_id"])
    logo_org: dict[tuple[int, str], set[str]] = {}
    for season, info in seasons.items():
        for rec in info["pages"].values():
            for row in (rec.get("page") or {}).get("schedule_rows", []):
                if row["opponent_team_season_id"] and row["opponent_logo_org_id"]:
                    logo_org.setdefault((season, row["opponent_team_season_id"]), set()).add(row["opponent_logo_org_id"])

    cells: dict[str, dict[str, Any]] = {}

    def cell(key: str, season: int, org: str | None) -> dict[str, Any]:
        if key not in cells:
            cells[key] = {"cell_key": key, "season": season, "ncaa_org_id": org, "provider_key": None,
                          "team_name": None, "ncaa_team_season_id": None, "expected_sources": [],
                          "graph": None, "e2": None, "e3": None, "e4": [], "e5": None, "e6": None, "flags": []}
        return cells[key]

    def add_source(c: dict[str, Any], source: str) -> None:
        if source not in c["expected_sources"]:
            c["expected_sources"].append(source)

    for season in DELIVERY_SEASONS:
        info = seasons[season]
        per_org: dict[str, list[str]] = {}
        for ts, rec in info["pages"].items():
            page = rec.get("page")
            org = page.get("org_id") if page else None
            c = cell(_key(org, ts, season), season, org)
            add_source(c, "E1")
            c["graph"] = rec
            c["ncaa_team_season_id"] = ts
            if org:
                per_org.setdefault(org, []).append(ts)
        for org, tss in per_org.items():
            if len(tss) > 1:
                cells[_key(org, None, season)]["flags"].append("DUPLICATE_TEAM_SEASON_PAGES:" + ",".join(sorted(tss)))
        for ts, failure in info["failures"].items():
            orgs = selector_org.get((season, ts), set()) or logo_org.get((season, ts), set())
            org = next(iter(orgs)) if len(orgs) == 1 else None
            c = cell(_key(org, ts, season), season, org)
            add_source(c, "E1")
            if c.get("graph") is not None:
                c["flags"].append(f"FAILED_CAPTURE_FOR_ORGANIZATION_WITH_PAGE:{ts}")
            c["ncaa_team_season_id"] = c["ncaa_team_season_id"] or ts
            c["capture_failure"] = {"condition": failure.get("condition"), "attempts": len(failure.get("attempts") or []),
                                    "org_source": ("SEASON_SELECTOR_ADJACENT" if selector_org.get((season, ts))
                                                   else ("OPPONENT_LOGO" if logo_org.get((season, ts)) else None))}
            if len(orgs) > 1:
                c["flags"].append("FAILED_CAPTURE_ORG_AMBIGUOUS")
        for pair_row in info["binding"]["census"]:
            for absent in pair_row.get("pairs_absent_classified", []):
                if absent["classification"] != "IN_SEASON_TEAM_SEASON_ABSENT_FROM_BOUND":
                    continue
                org = absent.get("page_org_id") or ts_org.get((season, absent["team_season_id"]))
                c = cell(_key(org, absent["team_season_id"], season), season, org)
                c["flags"].append(f"SUPERSEDED_PAIR_ABSENT_FROM_BOUND:{pair_row['identity']}:{absent['raw_sha256']}")
        # E4: adjacent-season selectors naming a team-season the graph never discovered
        for (other_season, ts), orgs in selector_org.items():
            if other_season != season or ts in info["discovered"]:
                continue
            for org in sorted(orgs):
                c = cell(_key(org, None, season), season, org)
                add_source(c, "E4")
                adjacent_codes = sorted({str(code_of.get((s, org))) for s in (season - 1, season + 1)
                                         if (s, org) in code_of})
                c["e4"].append({"team_season_id": ts, "adjacent_codes": adjacent_codes})
                c["ncaa_team_season_id"] = c["ncaa_team_season_id"] or ts
    # E2 official team history
    for (org, season), row in history["rows"].items():
        c = cell(_key(org, None, season), season, org)
        add_source(c, "E2")
        c["e2"] = row
        if row.get("variant_conflict"):
            c["flags"].append("OFFICIAL_HISTORY_VARIANT_CONFLICT")

    # identity binding NCAA organization <-> CFBD team (2016-2023 evidence only)
    cfbd_union_by_season = {}
    for season in TWO_SOURCE_SEASONS:
        cfbd_union_by_season[season], _ = union_cfbd([cfbd["fbs"][season], cfbd["fcs"][season]])
    evidence_games = [g for season in TWO_SOURCE_SEASONS for g in cfbd_union_by_season[season]]
    org_games: dict[str, list[tuple[str, int, int]]] = {}
    org_names: dict[str, set[str]] = {}
    for season, info in seasons.items():
        if season not in DELIVERY_SEASONS:
            continue
        for ts, rec in info["pages"].items():
            page = rec.get("page")
            if not page or not page.get("org_id"):
                continue
            org = page["org_id"]
            if page.get("team_name") and page.get("team_name_source") == "HEADER_LOGO_ALT":
                org_names.setdefault(org, set()).add(page["team_name"])
            for row in page["schedule_rows"]:
                opp_org = ts_org.get((season, row["opponent_team_season_id"])) if row["opponent_team_season_id"] else None
                if opp_org and row["opponent_name"] and row["opponent_logo_org_id"] == opp_org:
                    org_names.setdefault(opp_org, set()).add(row["opponent_name"])
                if season not in TWO_SOURCE_SEASONS or row["status"] != "COMPLETED" or not row["date"]:
                    continue
                own_code = code_of.get((season, org))
                opp_code = code_of.get((season, opp_org)) if opp_org else None
                if own_code in DIVISION_I_CODES or opp_code in DIVISION_I_CODES:
                    org_games.setdefault(org, []).append((row["date"], row["team_points"], row["opponent_points"]))
    for org, name in history["names"].items():
        org_names.setdefault(org, set()).add(name)
    cfbd_names: dict[str, set[str]] = {}
    for game in evidence_games:
        for team, name in ((game["home_id"], game["home_team"]), (game["away_id"], game["away_team"])):
            if team and name:
                cfbd_names.setdefault(team, set()).add(name)
    canonical_to_cfbd = {v: k for k, v in cfbd["registry"]["cfbd_to_canonical"].items()}
    for canonical, aliases in cfbd["registry"]["canonical_aliases"].items():
        team = canonical_to_cfbd.get(canonical)
        if team:
            cfbd_names.setdefault(team, set()).update(aliases)
    bindings = bind_organizations(org_games, org_names, evidence_games, cfbd_names, expansions)
    for org in org_names:
        bindings.setdefault(org, {"org_id": org, "cfbd_team_id": None, "rule": None, "reason": "NO_SCHEDULE_EVIDENCE",
                                  "n_games": 0, "name_candidates": [], "best_fingerprint": [None, 0],
                                  "runner_up_fingerprint": 0, "candidate_fingerprints": {}})
    cfbd_to_org = {b["cfbd_team_id"]: org for org, b in bindings.items() if b["cfbd_team_id"]}

    # E3 / E5 / E6 provider expectations through the binding
    def provider_expect(source: str, team: str, season: int, payload: dict[str, Any]) -> None:
        org = cfbd_to_org.get(team)
        if org:
            c = cell(_key(org, None, season), season, org)
        else:
            key = f"cfbd:{team}:{season}"
            c = cells.setdefault(key, {"cell_key": key, "season": season, "ncaa_org_id": None,
                                       "provider_key": f"SRC-002:TEAM:{team}", "team_name": payload.get("name"),
                                       "ncaa_team_season_id": None, "expected_sources": [], "graph": None, "e2": None,
                                       "e3": None, "e4": [], "e5": None, "e6": None, "flags": []})
        add_source(c, source)
        c[source.lower()] = payload

    for row in cfbd["membership"]:
        season = int(row["season"])
        if season in DELIVERY_SEASONS:
            provider_expect("E3", _cfbd_id(row["program_id"]), season,
                            {"classification": row.get("classification"), "conference": row.get("conference"),
                             "name": row.get("display_name")})
    for season in DELIVERY_SEASONS:
        seen: dict[str, dict[str, Any]] = {}
        for game in cfbd["fbs"][season]:
            for team, name, cls in ((game["home_id"], game["home_team"], game["home_classification"]),
                                    (game["away_id"], game["away_team"], game["away_classification"])):
                if team and cls in ("fbs", "fcs"):
                    seen.setdefault(team, {"classification": cls, "name": name, "games": 0})["games"] += 1
        for team, payload in seen.items():
            provider_expect("E5", team, season, payload)
    e3_2023 = {_cfbd_id(r["program_id"]) for r in cfbd["membership"] if int(r["season"]) == 2023}
    for program in e6.get("programs") or []:
        team = _cfbd_id(program["program_id"])
        if team in e3_2023:
            for season in SINGLE_SOURCE_SEASONS:
                provider_expect("E6", team, season, {"classification": program.get("classification"),
                                                     "name": program.get("display_name")})

    # dispositions, one per cell
    for c in cells.values():
        assign_program_season_disposition(c)
    transitions, across = observe_transitions(cells)
    for c in cells.values():
        tr = transitions.get((c["ncaa_org_id"], c["season"]))
        c["transition_observed"] = bool(tr)
        if tr:
            c["transition"] = tr
        gap = across.get((c["ncaa_org_id"], c["season"]))
        if gap:
            c["transition_across_unobserved"] = gap
            c["flags"].append("TRANSITION_ACROSS_UNOBSERVED_SEASON")
    return {"graph": graph, "history": history, "cfbd": cfbd, "e6": e6, "cells": cells, "bindings": bindings,
            "transitions": transitions, "transitions_across_unobserved": across, "ts_org": ts_org, "code_of": code_of,
            "cfbd_union_by_season": cfbd_union_by_season}


#: Flags that make a program-season cell CONFLICT; the reason is the first triggering flag (contract conflict_rules).
CELL_CONFLICT_FLAGS = ("DUPLICATE_TEAM_SEASON_PAGES", "SUPERSEDED_PAIR_ABSENT_FROM_BOUND",
                       "FAILED_CAPTURE_FOR_ORGANIZATION_WITH_PAGE", "OFFICIAL_HISTORY_VARIANT_CONFLICT")


def assign_program_season_disposition(c: dict[str, Any]) -> None:
    """Exactly one disposition per expected key (contract program_season_dispositions)."""
    e2 = c.get("e2")
    e2_raw = e2.get("division_label") if e2 else None
    e2_label = E2_LABEL_MAP.get(e2_raw) if e2_raw else None
    rec = c.get("graph")
    page = rec.get("page") if rec else None
    division_code = division_label = None
    authority = "NONE"
    header = None
    disposition = reason = None
    if c["provider_key"]:
        disposition, reason = "IDENTITY_UNRESOLVED", "PROVIDER_KEY_NOT_BOUND_TO_NCAA_ORGANIZATION"
    elif rec is not None:
        if not rec["rehash_ok"]:
            disposition, reason = "PAYLOAD_MISSING", "RAW_REHASH_MISMATCH"
        elif not rec.get("identity_ok"):
            disposition, reason = "IDENTITY_UNRESOLVED", "PAGE_IDENTITY_MISMATCH"
        elif page["decode"]["decode_state"] != "DECODED":
            disposition, reason = "IDENTITY_UNRESOLVED", page["decode"]["decode_state"]
        else:
            division_code, division_label = page["decode"]["code"], page["decode"]["label"]
            authority = "GRAPH_PAGE"
            header = (page.get("header_record") or {}).get("text")
            official_code = E2_LABEL_TO_CODE.get(e2_raw) if e2_raw else None
            if e2_raw == "D-III" and division_code == "3":
                # Consistent but non-proving: code 3 stays OUTSIDE_DI_CODE_3 / INFERRED_UNPROVEN.
                c["flags"].append("OFFICIAL_D_III_OVER_CODE_3")
                disposition, reason = "NOT_APPLICABLE", "OUTSIDE_DIVISION_I"
            elif e2_raw and official_code != division_code:
                disposition, reason = "CONFLICT", f"OFFICIAL_DIVISION_DISAGREEMENT:graph={division_code}:history={e2_raw}"
            elif division_code in DIVISION_I_CODES:
                if page.get("header_record") is None:
                    disposition, reason = "CANDIDATE_ONLY", "HEADER_RECORD_UNPARSED"
                else:
                    disposition, reason = "VERIFIED_PRESENT", None
            else:
                disposition, reason = "NOT_APPLICABLE", "OUTSIDE_DIVISION_I"
        if not c["ncaa_org_id"] and disposition not in ("PAYLOAD_MISSING",):
            disposition, reason = "IDENTITY_UNRESOLVED", "ORGANIZATION_UNRESOLVED"
    elif c.get("capture_failure"):
        disposition, reason = "PAYLOAD_MISSING", f"CAPTURE_FAILED:{c['capture_failure']['condition']}"
    else:
        disposition, reason = "SOURCE_ABSENT", "NOT_IN_BOUND_GRAPH"
        if e2_label:
            # The official label is the division authority; no page code was observed, so none is recorded.
            division_label, authority = e2_label, "OFFICIAL_TEAM_HISTORY_ROW"
        elif e2_raw:
            disposition, reason = "IDENTITY_UNRESOLVED", f"UNKNOWN_OFFICIAL_LABEL:{e2_raw}"
    triggering = [f for f in c["flags"] if f.startswith(CELL_CONFLICT_FLAGS)]
    if triggering:
        disposition, reason = "CONFLICT", triggering[0]
        if any(f.startswith("DUPLICATE_TEAM_SEASON_PAGES") for f in triggering):
            division_code, division_label, authority = None, None, "NONE"
    if page:
        c["team_name"] = page.get("team_name")
    elif e2:
        c["team_name"] = e2.get("team_name")
    if division_label in ("FBS", "FCS"):
        in_di = True
    elif division_label in ("DII", "DIII", "OUTSIDE_DI_CODE_3"):
        in_di = False
    else:
        in_di = None
    c.update(disposition=disposition, disposition_reason=reason, division_code_observed=division_code,
             division_label=division_label if division_code or authority != "NONE" else None,
             division_authority=authority, header_record_wlt=header,
             conference_official=(e2.get("conference") if e2 and e2.get("conference") else "NOT_YET_AUDITED"),
             in_division_i_population=in_di,
             observations={"cfbd_e3_classification": (c.get("e3") or {}).get("classification"),
                           "src002_e5_classification": (c.get("e5") or {}).get("classification"),
                           "e6_classification": (c.get("e6") or {}).get("classification"),
                           "team_history_label": e2_raw,
                           "team_history_record_state": e2.get("record_state") if e2 else None})
    if disposition in ("SOURCE_ABSENT", "IDENTITY_UNRESOLVED") and authority == "NONE" and not division_code:
        c["division_label"] = "UNKNOWN_NOT_PROJECTED" if disposition == "SOURCE_ABSENT" else None
        c["in_division_i_population"] = None


def observe_transitions(cells: dict[str, dict[str, Any]]
                        ) -> tuple[dict[tuple[str, int], dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    """Contemporaneous page-code changes: between consecutive seasons (TRANSITION_OBSERVED) and across seasons that
    have no decoded page (TRANSITION_ACROSS_UNOBSERVED_SEASON, never projected into the unobserved seasons)."""
    codes: dict[str, dict[int, str]] = {}
    for c in cells.values():
        if c["ncaa_org_id"] and c.get("division_authority") == "GRAPH_PAGE" and c.get("division_code_observed"):
            codes.setdefault(c["ncaa_org_id"], {})[c["season"]] = c["division_code_observed"]
    consecutive, across = {}, {}
    for org, by_season in codes.items():
        observed = sorted(by_season)
        for earlier, later in zip(observed, observed[1:]):
            if by_season[later] == by_season[earlier]:
                continue
            entry = {"from_code": by_season[earlier], "to_code": by_season[later], "from_season": earlier,
                     "rule": "contemporaneous codes on each season's own page"}
            if later == earlier + 1:
                consecutive[(org, later)] = entry
            else:
                across[(org, later)] = {**entry, "unobserved_seasons": list(range(earlier + 1, later))}
    return consecutive, across


# ---------------------------------------------------------------------------------------------- M2: contests

PAIR_RANK = {"FBS": 0, "FCS": 1, "DII": 2, "OUTSIDE_DI_CODE_3": 3, "UNRESOLVED": 4, "NON_NCAA": 5}
#: Game-grain inconsistencies that make a contest CONFLICT in every season (contract contest_grain.mirror_disagreement,
#: duplicate_pair_date, participants).
MIRROR_FLAG_PREFIXES = ("MIRROR_SCORE_DISAGREEMENT", "MIRROR_STATUS_DISAGREEMENT", "MIRROR_DATE_DISAGREEMENT",
                        "MIRROR_SITE_DISAGREEMENT", "CONTEST_PARTICIPANTS_INCONSISTENT", "CONTEST_SEASON_INCONSISTENT",
                        "DUPLICATE_PAIR_DATE")


def contest_term(season: int, contest_date: str | None) -> str:
    return "SPRING" if season == 2020 and contest_date and contest_date >= SPRING_2020_FROM else "FALL"


def contest_term_observed(season: int, dates: list[str]) -> str:
    """Term from every observed date: 2020 without a date or straddling 2021-01-16 is UNRESOLVED (never projected)."""
    if season != 2020:
        return "FALL"
    terms = {contest_term(season, d) for d in dates if d}
    return terms.pop() if len(terms) == 1 else "UNRESOLVED"


def mirror_flags(contest: dict[str, Any]) -> list[str]:
    return [f for f in contest["flags"] if f.startswith(MIRROR_FLAG_PREFIXES)]


def _pair_label(code: str | None, label: str | None, external: bool) -> str:
    if external:
        return "NON_NCAA"
    if code in ("11", "12", "2", "3"):
        return {"11": "FBS", "12": "FCS", "2": "DII", "3": "OUTSIDE_DI_CODE_3"}[code]
    return "UNRESOLVED"


def classification_pair(left: str, right: str) -> str:
    return "-".join(sorted((left, right), key=lambda x: PAIR_RANK.get(x, 9)))


def build_contests(m1: dict[str, Any], cfbd_by_season: dict[int, list[dict[str, Any]]],
                   expansions: dict[str, str]) -> dict[str, Any]:
    """Game-grain contests from mirrored page observations, two-source reconciliation 2016-2023 and orientations.

    ``m1`` holds the program-season outputs read back from the M1 stage: ``observations`` (every schedule row of
    every bound page), ``pages`` (season, team-season -> organization and decode), ``cells`` and ``bindings``.
    """
    pages = {(p["season"], p["team_season_id"]): p for p in m1["pages"]}
    cells_by_org = {(c["ncaa_org_id"], c["season"]): c for c in m1["cells"] if c["ncaa_org_id"]}
    cells_by_ts = {(c["ncaa_team_season_id"], c["season"]): c for c in m1["cells"] if c["ncaa_team_season_id"]}
    binding = {b["org_id"]: b["cfbd_team_id"] for b in m1["bindings"] if b["cfbd_team_id"]}
    cfbd_to_org = {v: k for k, v in binding.items()}

    def participant(season: int, ts: str | None, logo_org: str | None, name: str | None) -> dict[str, Any]:
        if ts is None:
            key = "ext:" + normalize_name(name or "", expansions)
            return {"key": key, "external": True, "org_id": None, "team_season_id": None, "team_name": name,
                    "division_code": None, "membership": "NON_NCAA", "cell_disposition": None}
        page = pages.get((season, ts))
        org = page["org_id"] if page and page.get("org_id") else None
        org_source = "PAGE" if org else None
        if org is None and logo_org:
            org, org_source = logo_org, "OPPONENT_LOGO"
        c = cells_by_org.get((org, season)) if org else cells_by_ts.get((ts, season))
        code = c.get("division_code_observed") if c and c.get("division_authority") == "GRAPH_PAGE" else None
        membership = ("DIVISION_I" if c and c.get("in_division_i_population") is True else
                      "OUTSIDE_DIVISION_I" if c and c.get("in_division_i_population") is False else "UNRESOLVED")
        return {"key": f"org:{org}" if org else f"ts:{ts}", "external": False, "org_id": org, "org_source": org_source,
                "team_season_id": ts, "team_name": (page or {}).get("team_name") or name, "division_code": code,
                "membership": membership, "cell_disposition": c.get("disposition") if c else None}

    grouped: dict[str, dict[str, Any]] = {}
    for obs in m1["observations"]:
        season = obs["season"]
        owner = participant(season, obs["page_team_season_id"], None, obs.get("page_team_name"))
        other = participant(season, obs["opponent_team_season_id"], obs["opponent_logo_org_id"], obs["opponent_name"])
        if obs["ncaa_contest_id"]:
            key = f"ncaa:{obs['ncaa_contest_id']}"
        else:
            key = "nolink:%s:%s:%s" % (season, obs["date"] or "nodate", "|".join(sorted((owner["key"], other["key"]))))
        g = grouped.setdefault(key, {"contest_key": key, "season": season, "observations": [], "participants": {}})
        g["observations"].append({**obs, "owner_key": owner["key"], "other_key": other["key"]})
        g["participants"].setdefault(owner["key"], owner)
        if other["key"] not in g["participants"] or g["participants"][other["key"]]["team_season_id"] is None:
            g["participants"][other["key"]] = other
        if g["season"] != season:
            g.setdefault("flags", []).append("CONTEST_SEASON_INCONSISTENT")

    contests = []
    for key, g in grouped.items():
        flags = list(g.get("flags", []))
        parts = list(g["participants"].values())
        if len(parts) != 2:
            flags.append(f"CONTEST_PARTICIPANTS_INCONSISTENT:{len(parts)}")
            parts = sorted(parts, key=lambda p: (p["external"], p["key"]))[:2]
            if len(parts) < 2:
                # Never deleted: the missing second participant is an explicit unresolved placeholder.
                parts.append({"key": f"unresolved:{key}", "external": False, "org_id": None, "org_source": None,
                              "team_season_id": None, "team_name": None, "division_code": None,
                              "membership": "UNRESOLVED", "cell_disposition": None})
        a, b = sorted(parts, key=lambda p: (p["external"], p["key"]))
        division_i = any(p["division_code"] in DIVISION_I_CODES or p["membership"] == "DIVISION_I" for p in (a, b))
        unresolved = any(p["membership"] == "UNRESOLVED" and not p["external"] for p in (a, b))
        if not division_i and not unresolved:
            continue
        if not division_i:
            flags.append("INCLUDED_FOR_UNRESOLVED_DIVISION_I_MEMBERSHIP")
        obs_a = [o for o in g["observations"] if o["owner_key"] == a["key"]]
        obs_b = [o for o in g["observations"] if o["owner_key"] == b["key"]]
        for o in g["observations"]:
            flags.extend(f for f in o["flags"] if f not in flags and f != "NO_CONTEST_LINK")
        roles = []
        neutral_site = None
        for side, rows in (("A", obs_a), ("B", obs_b)):
            for o in rows:
                if o["neutral_site"]:
                    roles.append("NEUTRAL")
                    neutral_site = neutral_site or o["neutral_site"]
                elif o["page_team_marked_away"]:
                    roles.append("HOME_B" if side == "A" else "HOME_A")
                else:
                    roles.append("HOME_A" if side == "A" else "HOME_B")
        if "NEUTRAL" in roles:
            site = "NEUTRAL"
            if len(set(roles)) > 1:
                flags.append("MIRROR_SITE_PARTIALLY_STATED")
        elif len(set(roles)) == 1:
            site = roles[0]
        else:
            site = "UNKNOWN"
            flags.append("MIRROR_SITE_DISAGREEMENT")
        scores = set()
        statuses = set()
        dates = set()
        events = sorted({o["event_label"] for o in g["observations"] if o["event_label"]})
        for o in obs_a:
            statuses.add(o["status"])
            dates.add(o["date"])
            if o["team_points"] is not None:
                scores.add((o["team_points"], o["opponent_points"]))
        for o in obs_b:
            statuses.add(o["status"])
            dates.add(o["date"])
            if o["team_points"] is not None:
                scores.add((o["opponent_points"], o["team_points"]))
        observed_dates = sorted({d for d in dates if d})
        # Disagreeing mirrors: the game-grain value is null, every observed value is retained (never one chosen).
        if len(scores) > 1:
            flags.append("MIRROR_SCORE_DISAGREEMENT")
            a_pts, b_pts = None, None
        else:
            a_pts, b_pts = next(iter(scores)) if scores else (None, None)
        if len(statuses) > 1:
            flags.append("MIRROR_STATUS_DISAGREEMENT")
            status = "MIRROR_DISAGREEMENT"
        elif statuses:
            status = next(iter(statuses))
        else:  # only reachable with inconsistent participants (already flagged); no status is projected
            status = "MIRROR_DISAGREEMENT"
        if len(observed_dates) > 1:
            flags.append("MIRROR_DATE_DISAGREEMENT")
            contest_date = None
        else:
            contest_date = observed_dates[0] if observed_dates else None
        la = _pair_label(a["division_code"], None, a["external"])
        lb = _pair_label(b["division_code"], None, b["external"])
        contests.append({
            "contest_key": key, "ncaa_contest_id": key.split(":", 1)[1] if key.startswith("ncaa:") else None,
            "season": g["season"], "term": contest_term_observed(g["season"], observed_dates), "contest_date": contest_date,
            "contest_dates_observed": observed_dates, "site": site, "neutral_site_text": neutral_site,
            "mirror_scores_observed": [list(s) for s in sorted(scores)] if len(scores) > 1 else None,
            "contest_statuses_observed": sorted(statuses) if len(statuses) > 1 else None,
            "event_labels": events, "contest_status": status, "competitive": status == "COMPLETED",
            "a_key": a["key"], "a_org_id": a["org_id"], "a_team_season_id": a["team_season_id"],
            "a_team_name": a["team_name"], "a_division_code": a["division_code"], "a_division_label": la,
            "a_membership": a["membership"], "a_points": a_pts,
            "b_key": b["key"], "b_org_id": b["org_id"], "b_team_season_id": b["team_season_id"],
            "b_team_name": b["team_name"], "b_division_code": b["division_code"], "b_division_label": lb,
            "b_membership": b["membership"], "b_points": b_pts, "b_external": b["external"],
            "classification_pair": classification_pair(la, lb), "mirror_observation_count": len(g["observations"]),
            "source": "NCAA_GRAPH", "flags": sorted(set(flags))})

    # Several contest keys for one season, unordered pair and date are each CONFLICT; none is dropped.
    by_pair_date: dict[tuple[int, frozenset, str], list[dict[str, Any]]] = {}
    for c in contests:
        if c["contest_date"]:
            by_pair_date.setdefault((c["season"], frozenset((c["a_key"], c["b_key"])), c["contest_date"]), []).append(c)
    for group in by_pair_date.values():
        if len(group) > 1:
            for c in group:
                c["flags"] = sorted(set(c["flags"]) | {"DUPLICATE_PAIR_DATE"})
                c["duplicate_pair_date_keys"] = sorted(x["contest_key"] for x in group if x is not c)

    reconcile_contests(contests, cfbd_by_season, binding, cfbd_to_org, cells_by_org)
    orientations = [row for c in contests for row in orient(c)]
    return {"contests": sorted(contests, key=lambda c: (c["season"], c["contest_date"] or "", c["contest_key"])),
            "orientations": orientations}


def _days(a: str, b: str) -> int:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def _within(game: dict[str, Any], contest: dict[str, Any], days: int = FORWARD_MATCH_DAYS) -> bool:
    """Any observed NCAA page date within ``days`` of a CFBD candidate local date (contract cfbd_date_basis)."""
    for observed in contest["contest_dates_observed"]:
        distance = cfbd_days(game, observed)
        if distance is not None and distance <= days:
            return True
    return False


def _oriented(game: dict[str, Any], team: str | None) -> tuple[Any, Any]:
    """(own points, opponent points) of a CFBD row for one CFBD team id."""
    if game["home_id"] == team:
        return game["home_points"], game["away_points"]
    return game["away_points"], game["home_points"]


def _membership(cell: dict[str, Any] | None) -> str:
    if cell and cell.get("in_division_i_population") is True:
        return "DIVISION_I"
    if cell and cell.get("in_division_i_population") is False:
        return "OUTSIDE_DIVISION_I"
    return "UNRESOLVED"


def _conflict(c: dict[str, Any], reason: str) -> None:
    c.update(reconciliation_state="CONFLICT", disposition="CONFLICT", disposition_reason=reason)


def reconcile_contests(contests: list[dict[str, Any]], cfbd_by_season: dict[int, list[dict[str, Any]]],
                       binding: dict[str, str], cfbd_to_org: dict[str, str],
                       cells_by_org: dict[tuple[str, int], dict[str, Any]]) -> None:
    """Forward (NCAA->CFBD) and reverse (CFBD->NCAA) joins for 2016-2023; 2024-2025 single source, never joined.

    Mirror inconsistencies (contract mirror_disagreement, duplicate_pair_date, participants) make a contest CONFLICT in
    every season after the joins, so its CFBD row is still claimed and never re-emitted as a second contest.
    """
    for c in contests:
        c["conflict_fields"] = []
        if c["season"] in SINGLE_SOURCE_SEASONS:
            c.update(reconciliation_state=SINGLE_SOURCE, exposure=EXPOSURE_2024_2025, cfbd_game_ids=[],
                     disposition="CANDIDATE_ONLY", disposition_reason="SINGLE_SOURCE_UNRECONCILED")
        else:
            c.update(exposure="NOT_APPLICABLE_2016_2023_RECONCILIATION_TRANCHE", cfbd_game_ids=[])
    cfbd_rows_added = []
    for season in TWO_SOURCE_SEASONS:
        games = cfbd_by_season[season]
        by_pair: dict[frozenset, list[dict[str, Any]]] = {}
        by_team: dict[str, list[dict[str, Any]]] = {}
        for g in games:
            if g["home_id"] and g["away_id"]:
                by_pair.setdefault(frozenset((g["home_id"], g["away_id"])), []).append(g)
            for t in (g["home_id"], g["away_id"]):
                if t:
                    by_team.setdefault(t, []).append(g)
        season_contests = [c for c in contests if c["season"] == season]
        edges: dict[str, list[str]] = {}
        reverse: dict[str, list[str]] = {}
        single: dict[str, list[str]] = {}
        for c in season_contests:
            ta, tb = binding.get(c["a_org_id"]) if c["a_org_id"] else None, binding.get(c["b_org_id"]) if c["b_org_id"] else None
            c["a_cfbd_team_id"], c["b_cfbd_team_id"] = ta, tb
            if not c["contest_dates_observed"]:
                continue
            if ta and tb:
                cands = [g for g in by_pair.get(frozenset((ta, tb)), []) if _within(g, c)]
                edges[c["contest_key"]] = [g["cfbd_game_id"] for g in cands]
                for g in cands:
                    reverse.setdefault(g["cfbd_game_id"], []).append(c["contest_key"])
            elif (ta or tb) and c["competitive"] and c["a_points"] is not None:
                team, own, other = (ta, c["a_points"], c["b_points"]) if ta else (tb, c["b_points"], c["a_points"])
                single[c["contest_key"]] = [g["cfbd_game_id"] for g in by_team.get(team, [])
                                            if _within(g, c) and _oriented(g, team) == (own, other)]
        game_by_id = {g["cfbd_game_id"]: g for g in games}
        single_claims: dict[str, int] = {}
        for cand in single.values():
            if len(cand) == 1:
                single_claims[cand[0]] = single_claims.get(cand[0], 0) + 1
        matched_games: set[str] = set()
        for c in season_contests:
            key = c["contest_key"]
            page_anomaly = [f for f in c["flags"] if f in ("RESULT_LETTER_CONTRADICTS_SCORE", "NEGATIVE_OVERTIME_MARKER")]
            if not c["contest_dates_observed"]:
                c.update(reconciliation_state="NOT_RECONCILED_DATE_MISSING", disposition="CANDIDATE_ONLY",
                         disposition_reason="CONTEST_DATE_MISSING")
            elif key in edges:
                cand = edges[key]
                if len(cand) == 1 and len(reverse.get(cand[0], [])) == 1:
                    g = game_by_id[cand[0]]
                    matched_games.add(g["cfbd_game_id"])
                    c["cfbd_game_ids"] = [g["cfbd_game_id"]]
                    c["cfbd_routes"] = g.get("routes")
                    conflicts = compare_with_cfbd(c, g)
                    c["conflict_fields"] = conflicts
                    route = ["CFBD_ROUTE_CONFLICT"] if g.get("route_conflict") else []
                    if conflicts or route:
                        _conflict(c, "FIELD_DISAGREEMENT:" + ",".join([x["field"] for x in conflicts] + route))
                    elif not c["competitive"]:
                        if g["completed"]:
                            _conflict(c, "NON_COMPETITIVE_STATUS_BUT_CFBD_GAME")
                        else:
                            c.update(reconciliation_state=RECONCILED, disposition="CANDIDATE_ONLY",
                                     disposition_reason="NON_COMPETITIVE_BOTH_SOURCES")
                    elif page_anomaly:
                        c.update(reconciliation_state=RECONCILED, disposition="CANDIDATE_ONLY",
                                 disposition_reason="PAGE_ANOMALY:" + ",".join(page_anomaly))
                    else:
                        c.update(reconciliation_state=RECONCILED, disposition="VERIFIED_PRESENT", disposition_reason=None)
                elif len(cand) == 0:
                    if not c["competitive"]:
                        c.update(reconciliation_state="NOT_RECONCILED_NON_COMPETITIVE", disposition="CANDIDATE_ONLY",
                                 disposition_reason=f"NON_COMPETITIVE_STATUS:{c['contest_status']}")
                    else:
                        c.update(reconciliation_state="SECOND_SOURCE_ABSENT", disposition="CANDIDATE_ONLY",
                                 disposition_reason="SECOND_SOURCE_ABSENT")
                else:
                    c["cfbd_game_ids"] = sorted(cand)
                    _conflict(c, "NOT_ONE_TO_ONE")
                    matched_games.update(cand)
            elif key in single:
                cand = single[key]
                if len(cand) == 1 and len(reverse.get(cand[0], [])) == 0 and single_claims.get(cand[0], 0) == 1:
                    matched_games.add(cand[0])
                    c["cfbd_game_ids"] = cand
                    c.update(reconciliation_state="MATCHED_SINGLE_BOUND_PARTICIPANT", disposition="CANDIDATE_ONLY",
                             disposition_reason="OPPONENT_IDENTITY_NOT_BOUND")
                else:
                    unbound_di = any(c[f"{s}_membership"] in ("DIVISION_I",) and not c.get(f"{s}_cfbd_team_id")
                                     for s in ("a", "b"))
                    c["cfbd_game_ids"] = sorted(cand)
                    if len(cand) > 1 or (len(cand) == 1 and (reverse.get(cand[0]) or single_claims.get(cand[0], 0) > 1)):
                        _conflict(c, "NOT_ONE_TO_ONE")
                        matched_games.update(cand)
                    elif unbound_di:
                        c.update(reconciliation_state="IDENTITY_UNRESOLVED", disposition="IDENTITY_UNRESOLVED",
                                 disposition_reason="PARTICIPANT_BINDING_UNRESOLVED")
                    else:
                        c.update(reconciliation_state="SECOND_SOURCE_ABSENT", disposition="CANDIDATE_ONLY",
                                 disposition_reason="SECOND_SOURCE_ABSENT")
            else:
                if not c["competitive"]:
                    c.update(reconciliation_state="NOT_RECONCILED_NON_COMPETITIVE", disposition="CANDIDATE_ONLY",
                             disposition_reason=f"NON_COMPETITIVE_STATUS:{c['contest_status']}")
                else:
                    c.update(reconciliation_state="IDENTITY_UNRESOLVED", disposition="IDENTITY_UNRESOLVED",
                             disposition_reason="PARTICIPANT_BINDING_UNRESOLVED")
        # Reverse: every in-scope CFBD row maps to exactly one contest or becomes an explicit cfbd: contest. Scope comes
        # from NCAA membership; provider classification only flags participants whose membership is unresolved.
        contest_by_key = {c["contest_key"]: c for c in season_contests}
        open_contests = [c for c in season_contests if not c["cfbd_game_ids"] and c["competitive"]
                         and c["a_points"] is not None and c["a_cfbd_team_id"] and c["b_cfbd_team_id"]]
        pending = []
        claims: dict[str, list[str]] = {}
        for g in games:
            gid = g["cfbd_game_id"]
            if gid in matched_games:
                continue
            sides = []
            for team, cls in ((g["home_id"], g["home_classification"]), (g["away_id"], g["away_classification"])):
                org = cfbd_to_org.get(team) if team else None
                cell = cells_by_org.get((org, season)) if org else None
                sides.append({"team": team, "org": org, "cell": cell, "membership": _membership(cell), "cls": cls})
            division_i = any(s["membership"] == "DIVISION_I" for s in sides)
            if not division_i and not any(s["membership"] == "UNRESOLVED" and s["cls"] in ("fbs", "fcs") for s in sides):
                continue
            near = []
            if all(s["org"] for s in sides) and g["home_points"] is not None and g["away_points"] is not None:
                orgs = {sides[0]["org"], sides[1]["org"]}
                for c in open_contests:
                    if ({c["a_org_id"], c["b_org_id"]} == orgs
                            and _oriented(g, c["a_cfbd_team_id"]) == (c["a_points"], c["b_points"])
                            and _within(g, c, SAME_PAIR_WINDOW_DAYS)):
                        near.append(c["contest_key"])
            pending.append((g, sides, division_i, near))
            for k in near:
                claims.setdefault(k, []).append(gid)
        for g, sides, division_i, near in pending:
            gid = g["cfbd_game_id"]
            if len(near) == 1 and len(claims[near[0]]) == 1:
                # Same pair, same score, dates outside the forward window: one contest, CONFLICT on date.
                c = contest_by_key[near[0]]
                c["cfbd_game_ids"] = [gid]
                c["cfbd_routes"] = g.get("routes")
                conflicts = [{"field": "date", "ncaa": c["contest_dates_observed"], "cfbd_local_dates": g["local_dates"],
                              "cfbd_start_utc": g["start_utc"]}]
                conflicts += [x for x in compare_with_cfbd(c, g) if x["field"] != "score"]
                c["conflict_fields"] = conflicts
                _conflict(c, "FIELD_DISAGREEMENT:" + ",".join(x["field"] for x in conflicts))
                continue
            unbound = any(not s["org"] and (s["cls"] in ("fbs", "fcs") or not division_i) for s in sides)
            row = cfbd_only_contest(g, season, sides, "IDENTITY_UNRESOLVED" if unbound else "SOURCE_ABSENT", division_i)
            if near:
                row["flags"] = sorted(set(row["flags"]) | {"POSSIBLE_DUPLICATE_OF:" + ",".join(sorted(near))})
                _conflict(row, "POSSIBLE_DUPLICATE_OF_NCAA_CONTEST")
            cfbd_rows_added.append(row)
    contests.extend(cfbd_rows_added)
    for c in contests:
        mirror = mirror_flags(c)
        if mirror and c["disposition"] != "CONFLICT":
            c.update(disposition="CONFLICT", disposition_reason="MIRROR_INCONSISTENT:" + ",".join(mirror))
            if c["season"] in TWO_SOURCE_SEASONS:
                c["reconciliation_state"] = "CONFLICT"


def compare_with_cfbd(c: dict[str, Any], g: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts = []
    home_is_a = g["home_id"] == c["a_cfbd_team_id"]
    g_a, g_b = (g["home_points"], g["away_points"]) if home_is_a else (g["away_points"], g["home_points"])
    if c["competitive"] and c["a_points"] is not None and (c["a_points"], c["b_points"]) != (g_a, g_b):
        conflicts.append({"field": "score", "ncaa": [c["a_points"], c["b_points"]], "cfbd": [g_a, g_b]})
    if c["site"] in ("NEUTRAL", "HOME_A", "HOME_B"):
        ncaa_neutral = c["site"] == "NEUTRAL"
        if bool(g["neutral_site"]) != ncaa_neutral:
            conflicts.append({"field": "neutral_site", "ncaa": c["site"], "cfbd": g["neutral_site"]})
        elif not ncaa_neutral:
            ncaa_home_a = c["site"] == "HOME_A"
            if ncaa_home_a != home_is_a:
                conflicts.append({"field": "home_orientation", "ncaa": c["site"],
                                  "cfbd_home_team_id": g["home_id"]})
    c["cfbd_local_dates"] = g["local_dates"]
    deltas = [d for d in (cfbd_days(g, observed) for observed in c["contest_dates_observed"]) if d is not None]
    if deltas and min(deltas) > 0:
        c["date_delta_days"] = min(deltas)
    return conflicts


def cfbd_only_contest(g: dict[str, Any], season: int, sides: list[dict[str, Any]], disposition: str,
                      division_i: bool) -> dict[str, Any]:
    """A CFBD row with no NCAA contest (contract reconciliation.cfbd_only_row).

    Nothing official observed this contest: site UNKNOWN, status NOT_OFFICIALLY_OBSERVED, never competitive, no points.
    The provider's home/away ids, points, completion, neutral flag and classifications stay observation fields only.
    """
    people = []
    for s, name in ((sides[0], g["home_team"]), (sides[1], g["away_team"])):
        cell = s["cell"] or {}
        code = cell.get("division_code_observed") if cell.get("division_authority") == "GRAPH_PAGE" else None
        people.append({"key": f"org:{s['org']}" if s["org"] else f"cfbdteam:{s['team']}", "org_id": s["org"],
                       "team_name": cell.get("team_name") or name, "code": code, "membership": s["membership"],
                       "team_season_id": cell.get("ncaa_team_season_id"), "cfbd_team_id": s["team"]})
    a, b = sorted(people, key=lambda p: p["key"])
    la, lb = _pair_label(a["code"], None, False), _pair_label(b["code"], None, False)
    flags = ["CFBD_ONLY_NOT_OFFICIALLY_OBSERVED"]
    if not division_i:
        flags.append("INCLUDED_FOR_UNRESOLVED_DIVISION_I_MEMBERSHIP")
    if g.get("route_conflict"):
        flags.append("CFBD_ROUTE_CONFLICT")
    local = g["local_dates"]
    return {"contest_key": f"cfbd:{g['cfbd_game_id']}", "ncaa_contest_id": None, "season": season,
            "term": contest_term_observed(season, local), "contest_date": local[0] if len(local) == 1 else None,
            "contest_dates_observed": local, "site": "UNKNOWN", "neutral_site_text": None, "event_labels": [],
            "mirror_scores_observed": None, "contest_statuses_observed": None,
            "contest_status": "NOT_OFFICIALLY_OBSERVED", "competitive": False,
            "a_key": a["key"], "a_org_id": a["org_id"], "a_team_season_id": a["team_season_id"],
            "a_team_name": a["team_name"], "a_division_code": a["code"], "a_division_label": la,
            "a_membership": a["membership"], "a_points": None,
            "b_key": b["key"], "b_org_id": b["org_id"], "b_team_season_id": b["team_season_id"],
            "b_team_name": b["team_name"], "b_division_code": b["code"], "b_division_label": lb,
            "b_membership": b["membership"], "b_points": None, "b_external": False,
            "classification_pair": classification_pair(la, lb), "mirror_observation_count": 0, "source": "CFBD_ONLY",
            "flags": sorted(flags), "cfbd_game_ids": [g["cfbd_game_id"]], "cfbd_routes": g.get("routes"),
            "reconciliation_state": disposition, "disposition": disposition,
            "disposition_reason": "CFBD_ONLY_NO_NCAA_CONTEST" if disposition == "SOURCE_ABSENT" else "CFBD_PARTICIPANT_NOT_BOUND",
            "exposure": "NOT_APPLICABLE_2016_2023_RECONCILIATION_TRANCHE", "conflict_fields": [],
            "a_cfbd_team_id": a["cfbd_team_id"], "b_cfbd_team_id": b["cfbd_team_id"],
            "cfbd_observation": {"home_id": g["home_id"], "away_id": g["away_id"], "home_team": g["home_team"],
                                 "away_team": g["away_team"], "home_points": g["home_points"],
                                 "away_points": g["away_points"], "completed": g["completed"],
                                 "neutral_site": g["neutral_site"], "home_classification": g["home_classification"],
                                 "away_classification": g["away_classification"], "start_utc": g["start_utc"],
                                 "season_type": g["season_type"], "week": g["week"]}}


EXTERNAL_MEMBERSHIPS = ("OUTSIDE_DIVISION_I", "NON_NCAA")


def orient(c: dict[str, Any]) -> list[dict[str, Any]]:
    """Exactly two orientation rows derived from one game row; a non-Division-I side gets the external view."""
    rows = []
    for side, me, other in ((0, "a", "b"), (1, "b", "a")):
        mine, theirs = c[f"{me}_points"], c[f"{other}_points"]
        if c["site"] == "NEUTRAL":
            site = "NEUTRAL"
        elif c["site"] in ("HOME_A", "HOME_B"):
            site = "HOME" if c["site"] == f"HOME_{me.upper()}" else "AWAY"
        else:
            site = "UNKNOWN"
        result = None
        if c["competitive"] and mine is not None and theirs is not None:
            result = "W" if mine > theirs else ("L" if mine < theirs else "T")
        membership = c.get(f"{me}_membership")
        rows.append({"contest_key": c["contest_key"], "ncaa_contest_id": c["ncaa_contest_id"], "season": c["season"],
                     "term": c["term"], "contest_date": c["contest_date"], "side": side,
                     "view": "EXTERNAL_OPPONENT_VIEW" if membership in EXTERNAL_MEMBERSHIPS else "PARTICIPANT_VIEW",
                     "team_membership": membership,
                     "team_key": c[f"{me}_key"], "team_org_id": c[f"{me}_org_id"],
                     "team_season_id": c[f"{me}_team_season_id"], "team_name": c[f"{me}_team_name"],
                     "team_division_label": c[f"{me}_division_label"], "opponent_key": c[f"{other}_key"],
                     "opponent_org_id": c[f"{other}_org_id"], "opponent_name": c[f"{other}_team_name"],
                     "opponent_division_label": c[f"{other}_division_label"], "site_for_team": site,
                     "team_points": mine, "opponent_points": theirs,
                     "margin": (mine - theirs) if result else None, "result": result,
                     "contest_status": c["contest_status"], "classification_pair": c["classification_pair"],
                     "disposition": c["disposition"], "reconciliation_state": c["reconciliation_state"],
                     "exposure": c["exposure"]})
    return rows


def schedule_reconciliation(m1: dict[str, Any], contests: list[dict[str, Any]],
                            orientations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per Division I program-season: page rows = contest rows = orientations; header W-L-T = derived results."""
    obs_by_page: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for o in m1["observations"]:
        obs_by_page.setdefault((o["season"], o["page_team_season_id"]), []).append(o)
    contest_keys_by_ts: dict[tuple[int, str], set[str]] = {}
    for c in contests:
        for s in ("a", "b"):
            if c[f"{s}_team_season_id"] and c["source"] == "NCAA_GRAPH":
                contest_keys_by_ts.setdefault((c["season"], c[f"{s}_team_season_id"]), set()).add(c["contest_key"])
    orient_by_ts: dict[tuple[int, str], int] = {}
    for o in orientations:
        if o["team_season_id"] and not o["contest_key"].startswith("cfbd:"):
            orient_by_ts[(o["season"], o["team_season_id"])] = orient_by_ts.get((o["season"], o["team_season_id"]), 0) + 1
    pages = {(p["season"], p["team_season_id"]): p for p in m1["pages"]}
    rows = []
    for cell in m1["cells"]:
        if cell.get("in_division_i_population") is not True or cell.get("division_authority") != "GRAPH_PAGE":
            continue
        ts, season = cell["ncaa_team_season_id"], cell["season"]
        page_rows = obs_by_page.get((season, ts), [])
        page = pages.get((season, ts)) or {}
        header = page.get("header_record")
        wins = losses = ties = 0
        for o in page_rows:
            if o["status"] != "COMPLETED" or "EXEMPTED_NOT_COUNTED" in o["flags"]:
                continue
            if o["team_points"] > o["opponent_points"]:
                wins += 1
            elif o["team_points"] < o["opponent_points"]:
                losses += 1
            else:
                ties += 1
        derived = {"wins": wins, "losses": losses, "ties": ties}
        header_triplet = None if header is None else {"wins": header["wins"], "losses": header["losses"],
                                                       "ties": header["ties"] or 0}
        n_contests = len(contest_keys_by_ts.get((season, ts), set()))
        n_orient = orient_by_ts.get((season, ts), 0)
        states = []
        if not (len(page_rows) == n_contests == n_orient):
            states.append("CARDINALITY_MISMATCH")
        if header_triplet is None:
            states.append("HEADER_RECORD_UNPARSED")
        elif header_triplet != derived:
            states.append("HEADER_RECORD_MISMATCH")
        rows.append({"cell_key": cell["cell_key"], "season": season, "ncaa_org_id": cell["ncaa_org_id"],
                     "ncaa_team_season_id": ts, "team_name": cell["team_name"], "division_label": cell["division_label"],
                     "page_rows": len(page_rows), "contest_rows": n_contests, "orientation_rows": n_orient,
                     "header_record": header_triplet, "derived_record": derived,
                     "header_note": page.get("header_note"), "state": "MATCH" if not states else ";".join(states)})
    return rows


def derive_subsets(contests: list[dict[str, Any]]) -> dict[str, Any]:
    fbs = sorted(c["contest_key"] for c in contests if c["a_division_code"] == "11" and c["b_division_code"] == "11")
    fcs = sorted(c["contest_key"] for c in contests if "12" in (c["a_division_code"], c["b_division_code"]))
    parent = {c["contest_key"] for c in contests}
    proof = {"FBS_ESTIMAND_SUBSET": {"rows": len(fbs), "distinct": len(set(fbs)), "subset_of_parent": set(fbs) <= parent},
             "FCS_SUBSET": {"rows": len(fcs), "distinct": len(set(fcs)), "subset_of_parent": set(fcs) <= parent}}
    result = {"FBS_ESTIMAND_SUBSET": fbs, "FCS_SUBSET": fcs, "proof": proof,
              "rules": {"FBS_ESTIMAND_SUBSET": "both participants decoded code 11 in that season",
                        "FCS_SUBSET": "at least one participant decoded code 12 in that season"}}
    problems = prove_subsets(contests, result)
    if problems:
        raise PopulationRefused("SUBSET_PROOF_FAILED", "; ".join(problems[:5]))
    return result


SUBSET_RULES = {"FBS_ESTIMAND_SUBSET": lambda c: c["a_division_code"] == "11" and c["b_division_code"] == "11",
                "FCS_SUBSET": lambda c: "12" in (c["a_division_code"], c["b_division_code"])}


def prove_subsets(contests: list[dict[str, Any]], subsets: dict[str, Any]) -> list[str]:
    """Bidirectional inclusion: every subset key is a parent row satisfying the rule; every such parent row is present."""
    parent = {c["contest_key"]: c for c in contests}
    problems = []
    for name, rule in SUBSET_RULES.items():
        keys = list(subsets.get(name) or [])
        if len(keys) != len(set(keys)):
            problems.append(f"{name}: duplicate keys")
        for key in keys:
            if key not in parent:
                problems.append(f"{name}: {key} absent from the parent")
            elif not rule(parent[key]):
                problems.append(f"{name}: {key} does not satisfy the subset rule")
        missing = sorted(k for k, c in parent.items() if rule(c) and k not in set(keys))
        if missing:
            problems.append(f"{name}: parent rows satisfying the rule are missing: {missing[:5]}")
    return problems


# ---------------------------------------------------------------------------------------------- summaries

def _count(rows: Iterable[dict[str, Any]], *keys: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        k = "|".join(str(row.get(key)) for key in keys)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def program_season_summary(cells: list[dict[str, Any]], graph_pages: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-season totals recomputed from cells (never from stored totals)."""
    summary = {}
    for season in DELIVERY_SEASONS:
        sc = [c for c in cells if c["season"] == season]
        di = [c for c in sc if c["in_division_i_population"] is True]
        pages = [p for p in graph_pages if p["season"] == season]
        summary[str(season)] = {
            "cells": len(sc), "by_disposition": _count(sc, "disposition"),
            "division_i_cells": len(di), "division_i_by_label_and_disposition": _count(di, "division_label", "disposition"),
            "division_i_unresolved_cells": sum(1 for c in sc if c["in_division_i_population"] is None),
            "graph_pages_by_code": _count(pages, "code"), "graph_decode_states": _count(pages, "decode_state"),
            "bat554_parser_crosscheck": _count([p.get("bat554_parser_crosscheck") or {"state": None} for p in pages], "state"),
            "by_expected_source": {s: sum(1 for c in sc if s in c["expected_sources"]) for s in ("E1", "E2", "E3", "E4", "E5", "E6")},
            "e4_division_i_adjacent": sum(1 for c in sc if c.get("e4") and any(x in ("11", "12") for e in c["e4"] for x in e["adjacent_codes"])),
            "payload_missing": sum(1 for c in sc if c["disposition"] == "PAYLOAD_MISSING"),
            "transitions_observed": sum(1 for c in sc if c.get("transition_observed")),
            "transitions_across_unobserved_season": sum(1 for c in sc if c.get("transition_across_unobserved")),
            "ranking_link_identity_mismatched_pages": sum(1 for p in pages if p.get("ranking_links_identity_mismatched")),
        }
    return summary


def contest_summary(contests: list[dict[str, Any]], orientations: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {}
    for season in DELIVERY_SEASONS:
        sc = [c for c in contests if c["season"] == season]
        summary[str(season)] = {
            "contests": len(sc), "orientations": sum(1 for o in orientations if o["season"] == season),
            "by_source": _count(sc, "source"), "by_classification_pair": _count(sc, "classification_pair"),
            "by_disposition": _count(sc, "disposition"), "by_reconciliation_state": _count(sc, "reconciliation_state"),
            "by_status": _count(sc, "contest_status"), "by_term": _count(sc, "term"),
            "fcs_fcs_contests": sum(1 for c in sc if c["classification_pair"] == "FCS-FCS"),
            "neutral_site_contests": sum(1 for c in sc if c["site"] == "NEUTRAL"),
        }
    return summary


# ---------------------------------------------------------------------------------------------- stage runners

def _strip_cell(c: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in c.items() if k not in ("graph",)}
    rec = c.get("graph")
    if rec:
        page = rec.get("page") or {}
        out["graph_page"] = {"raw_relative_path": rec["raw_relative_path"], "raw_sha256": rec["raw_sha256"],
                             "rehash_ok": rec["rehash_ok"], "identity_ok": rec.get("identity_ok"),
                             "decode_state": (page.get("decode") or {}).get("decode_state"),
                             "raw_division_codes": (page.get("decode") or {}).get("raw_codes"),
                             "all_ranking_link_codes": page.get("raw_division_codes"),
                             "ranking_links_identity_mismatched": page.get("ranking_links_identity_mismatched"),
                             "header_note": page.get("header_note"), "page_flags": page.get("flags")}
    return out


def run_program_season_stage(*, contract: dict[str, Any], contract_sha256: str, data_root: Path, repo_root: Path,
                             canonical_root: Path, manifest_root: Path, issued_at_utc: str) -> dict[str, Any]:
    payload = program_season_payload(contract=contract, contract_sha256=contract_sha256, data_root=data_root,
                                     repo_root=repo_root)
    result = materialize(canonical_root=canonical_root, manifest_root=manifest_root, stage="program-season",
                         contract_sha256=contract_sha256, inputs=payload["inputs"], upstream={}, files=payload["files"],
                         manifest_extra={"issued_at_utc": issued_at_utc, "label": "BAT-710 national program-season population",
                                         "row_counts": payload["row_counts"]})
    return {**result, "row_counts": payload["row_counts"]}


def program_season_payload(*, contract: dict[str, Any], contract_sha256: str, data_root: Path,
                           repo_root: Path) -> dict[str, Any]:
    """Every M1 output file as bytes plus the rows M2 reads back (no write)."""
    built = build_program_season(contract, data_root, repo_root)
    header = {"schema": SCHEMA_VERSION, "stage": "program-season", "contract_sha256": contract_sha256}
    graph_pages, observations, binding_census = [], [], {}
    for season, info in sorted(built["graph"]["seasons"].items()):
        binding_census[str(season)] = {
            "bound": {"identity": info["binding"]["bound"]["directory_identity"], "sha256": info["binding"]["bound"]["sha256"],
                      "captures": info["binding"]["bound"]["capture_count"], "failures": len(info["failures"]),
                      "issued_at_utc": info["binding"]["bound"]["issued_at_utc"], "discovered": len(info["discovered"])},
            "census": info["binding"]["census"], "raw_only_in_non_bound": info["raw_only_in_non_bound"],
            "captures_without_link_schema": info["captures_without_link_schema"],
            "use": "E4 adjacency for 2016 only" if season == 2015 else "delivery"}
        for ts, rec in sorted(info["pages"].items()):
            page = rec.get("page") or {}
            decode = page.get("decode") or {}
            completed = [r for r in page.get("schedule_rows", []) if r["status"] == "COMPLETED"
                         and "EXEMPTED_NOT_COUNTED" not in r["flags"]]
            hr = page.get("header_record")
            graph_pages.append({"season": season, "team_season_id": ts, "org_id": page.get("org_id"),
                                "team_name": page.get("team_name"), "team_name_source": page.get("team_name_source"),
                                "raw_relative_path": rec["raw_relative_path"], "raw_sha256": rec["raw_sha256"],
                                "rehash_ok": rec["rehash_ok"], "identity_ok": rec.get("identity_ok"),
                                "link_schema": rec.get("link_schema"), "selected_season_label": page.get("selected_season_label"),
                                "decode_state": decode.get("decode_state"), "code": decode.get("code"),
                                "label": decode.get("label"), "raw_codes": decode.get("raw_codes"),
                                "all_ranking_link_codes": page.get("raw_division_codes"),
                                "ranking_links_identity_mismatched": page.get("ranking_links_identity_mismatched"),
                                "header_record": hr, "header_note": page.get("header_note"),
                                "header_games_vs_completed_rows": None if hr is None else
                                ("MATCH" if hr["wins"] + hr["losses"] + (hr["ties"] or 0) == len(completed) else "MISMATCH"),
                                "completed_rows": len(completed), "schedule_rows": len(page.get("schedule_rows", [])),
                                "season_options": page.get("season_options"), "flags": page.get("flags"),
                                "bat554_parser_crosscheck": page.get("bat554_parser_crosscheck")})
            if season in DELIVERY_SEASONS:
                for row in page.get("schedule_rows", []):
                    observations.append({"season": season, "page_team_season_id": ts, "page_org_id": page.get("org_id"),
                                         "page_team_name": page.get("team_name"), "page_raw_sha256": rec["raw_sha256"],
                                         **row})
    cells = sorted((_strip_cell(c) for c in built["cells"].values()), key=lambda c: (c["season"], c["cell_key"]))
    for c in cells:
        if c["disposition"] not in PROGRAM_SEASON_DISPOSITIONS:
            raise PopulationRefused("DISPOSITION_OUTSIDE_VOCABULARY", c["cell_key"])
    external = [c for c in cells if c["disposition"] == "NOT_APPLICABLE"]
    bindings = sorted(built["bindings"].values(), key=lambda b: b["org_id"])
    history_rows = [built["history"]["rows"][k] for k in sorted(built["history"]["rows"])]
    diffs = observation_diffs(built, cells)
    delivered_pages = [p for p in graph_pages if p["season"] in DELIVERY_SEASONS]
    files = {
        "manifest_binding.json": json_bytes({"_header": header, "seasons": binding_census,
                                             "src015_file_count": built["graph"]["src015_file_count"],
                                             "src015_unreferenced": built["graph"]["src015_unreferenced"],
                                             "unreferenced_use": "never used as evidence"}),
        "page_decode.jsonl.gz": gzip_jsonl_bytes(header, graph_pages),
        "page_observations.jsonl.gz": gzip_jsonl_bytes(header, observations),
        "team_history.jsonl.gz": gzip_jsonl_bytes({**header, "junk_pages": built["history"]["junk_pages"],
                                                   "variants": built["history"]["variants"]}, history_rows),
        "identity_bindings.jsonl.gz": gzip_jsonl_bytes(header, bindings),
        "program_season_cells.jsonl.gz": gzip_jsonl_bytes(header, cells),
        "external_program_seasons.jsonl.gz": gzip_jsonl_bytes(header, external),
        "transitions.jsonl.gz": gzip_jsonl_bytes(header, [
            {"ncaa_org_id": org, "season": season, "kind": kind, **tr}
            for kind, source in (("TRANSITION_OBSERVED", built["transitions"]),
                                 ("TRANSITION_ACROSS_UNOBSERVED_SEASON", built["transitions_across_unobserved"]))
            for (org, season), tr in sorted(source.items())]),
        "observation_diffs.json": json_bytes({"_header": header, **diffs}),
        "season_summary.json": json_bytes({"_header": header, "seasons": program_season_summary(cells, delivered_pages)}),
    }
    inputs = {"bound_manifests": {s: v["bound"] for s, v in binding_census.items()},
              "input_bindings_sha256": stable_hash(contract["input_bindings"])}
    return {"files": files, "inputs": inputs,
            "row_counts": {"cells": len(cells), "pages": len(graph_pages), "observations": len(observations),
                           "bindings": len(bindings)},
            "m1": {"pages": delivered_pages, "observations": observations, "cells": cells, "bindings": bindings}}


def observation_diffs(built: dict[str, Any], cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Identity-level diffs per season against E3, E5, official team history and the BAT-652 spine (observation only)."""
    out: dict[str, Any] = {}
    overlap = {"FBS": [0, 0], "FCS": [0, 0], "D-II": [0, 0]}
    disagreements = []
    for c in cells:
        e2 = c.get("e2")
        gp = c.get("graph_page")
        if e2 and gp and gp.get("decode_state") == "DECODED" and e2.get("division_label") in overlap:
            overlap[e2["division_label"]][0] += 1
            if E2_LABEL_TO_CODE[e2["division_label"]] == c["division_code_observed"]:
                overlap[e2["division_label"]][1] += 1
            else:
                disagreements.append({"cell_key": c["cell_key"], "graph": c["division_code_observed"],
                                      "history": e2["division_label"]})
    code3_pages = [c for c in cells if (c.get("graph_page") or {}).get("decode_state") == "DECODED"
                   and c["division_code_observed"] == "3"]
    d3_over_code3 = sorted(c["cell_key"] for c in code3_pages if (c.get("e2") or {}).get("division_label") == "D-III")
    other_over_code3 = sorted(c["cell_key"] for c in code3_pages
                              if (c.get("e2") or {}).get("division_label") not in (None, "D-III"))
    out["decoding_proof_against_team_history"] = {
        "overlap_by_label": {k: v[0] for k, v in overlap.items()}, "agreement_by_label": {k: v[1] for k, v in overlap.items()},
        "overlap_total": sum(v[0] for v in overlap.values()), "disagreements": disagreements,
        "code_3": {"code_3_pages": len(code3_pages), "official_d_iii_over_code_3": d3_over_code3,
                   "other_official_label_over_code_3": other_over_code3,
                   "statement": (f"{len(code3_pages)} decoded code-3 pages; {len(d3_over_code3)} carry an official "
                                 f"D-III row (consistent, not a proof) and {len(other_over_code3)} another official label; "
                                 "OUTSIDE_DI_CODE_3 stays INFERRED_UNPROVEN")}}
    per_season = {}
    for season in DELIVERY_SEASONS:
        sc = [c for c in cells if c["season"] == season]
        rows = {"cfbd_e3_vs_graph": [], "src002_e5_vs_graph": [], "team_history_vs_graph": [], "unbound_provider_keys": []}
        for c in sc:
            obs = c["observations"]
            graph_label = c["division_label"] if c["division_authority"] == "GRAPH_PAGE" else None
            for field, key in (("cfbd_e3_classification", "cfbd_e3_vs_graph"), ("src002_e5_classification", "src002_e5_vs_graph")):
                value = obs.get(field)
                if value and graph_label and value.upper() != graph_label:
                    rows[key].append({"cell_key": c["cell_key"], "provider": value, "graph": graph_label,
                                      "disposition": c["disposition"]})
                if value and not graph_label and c["ncaa_org_id"]:
                    rows[key].append({"cell_key": c["cell_key"], "provider": value, "graph": None,
                                      "disposition": c["disposition"]})
            history_label = obs.get("team_history_label")
            if (history_label and graph_label and E2_LABEL_TO_CODE.get(history_label) != c["division_code_observed"]
                    and not (history_label == "D-III" and c["division_code_observed"] == "3")):
                rows["team_history_vs_graph"].append({"cell_key": c["cell_key"], "history": obs["team_history_label"],
                                                      "graph": graph_label})
            if c["provider_key"]:
                rows["unbound_provider_keys"].append({"cell_key": c["cell_key"], "sources": c["expected_sources"],
                                                      "name": c.get("team_name")})
        per_season[str(season)] = {k: {"count": len(v), "rows": v} for k, v in rows.items()}
    out["per_season"] = per_season
    out["bat652_spine"] = "computed in the contest stage season_summary.json (bat652_spine_identity_diff)"
    return out


def read_stage_outputs(manifest: dict[str, Any], names: Iterable[str]) -> dict[str, Any]:
    out = {}
    for name in names:
        path = Path(manifest["data_dir"]) / name
        if name.endswith(".jsonl.gz"):
            header, rows = read_gzip_jsonl(path)
            if header.get("contract_sha256") != manifest["manifest"]["identity_document"]["contract_sha256"]:
                raise PopulationRefused("CONTRACT_IDENTITY_MISMATCH", f"{path} header contract differs")
            out[name] = rows
        else:
            out[name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def run_contest_stage(*, contract: dict[str, Any], contract_sha256: str, data_root: Path, program_season_manifest: Path,
                      canonical_root: Path, manifest_root: Path, issued_at_utc: str) -> dict[str, Any]:
    m1_manifest = load_stage_manifest(program_season_manifest, stage="program-season", contract_sha256=contract_sha256)
    outputs = read_stage_outputs(m1_manifest, ["page_decode.jsonl.gz", "page_observations.jsonl.gz",
                                               "program_season_cells.jsonl.gz", "identity_bindings.jsonl.gz"])
    m1 = {"pages": [p for p in outputs["page_decode.jsonl.gz"] if p["season"] in DELIVERY_SEASONS],
          "observations": outputs["page_observations.jsonl.gz"], "cells": outputs["program_season_cells.jsonl.gz"],
          "bindings": outputs["identity_bindings.jsonl.gz"]}
    cfbd = load_cfbd_sources(contract, data_root)
    cfbd_by_season = {s: union_cfbd([cfbd["fbs"][s], cfbd["fcs"][s]])[0] for s in TWO_SOURCE_SEASONS}
    route_conflicts = {s: union_cfbd([cfbd["fbs"][s], cfbd["fcs"][s]])[1] for s in TWO_SOURCE_SEASONS}
    expansions = contract["reconciliation"]["participant_resolution"]["token_expansions"]
    built = build_contests(m1, cfbd_by_season, expansions)
    contests, orientations = built["contests"], built["orientations"]
    for c in contests:
        if c["disposition"] not in CONTEST_DISPOSITIONS:
            raise PopulationRefused("DISPOSITION_OUTSIDE_VOCABULARY", c["contest_key"])
        if c["season"] in SINGLE_SOURCE_SEASONS and (c["disposition"] == "VERIFIED_PRESENT" or c["reconciliation_state"] != SINGLE_SOURCE):
            raise PopulationRefused("SINGLE_SOURCE_PROMOTED", c["contest_key"])
    keys = [c["contest_key"] for c in contests]
    if len(keys) != len(set(keys)) or len(orientations) != 2 * len(contests):
        raise PopulationRefused("CONTEST_GRAIN_VIOLATION", "duplicate contest keys or orientation count != 2x contests")
    reverse = [{"cfbd_game_id": gid, "season": c["season"], "contest_key": c["contest_key"],
                "disposition": c["disposition"], "reconciliation_state": c["reconciliation_state"]}
               for c in contests for gid in c.get("cfbd_game_ids") or []]
    schedule = schedule_reconciliation(m1, contests, orientations)
    subsets = derive_subsets(contests)
    header = {"schema": SCHEMA_VERSION, "stage": "contest", "contract_sha256": contract_sha256,
              "program_season_identity": m1_manifest["identity"]}
    spine = bat652_spine_diff(contract, data_root, m1["cells"], m1["bindings"])
    files = {
        "contests.jsonl.gz": gzip_jsonl_bytes(header, contests),
        "orientations.jsonl.gz": gzip_jsonl_bytes(header, orientations),
        "cfbd_reverse.jsonl.gz": gzip_jsonl_bytes(header, reverse),
        "schedule_reconciliation.jsonl.gz": gzip_jsonl_bytes(header, schedule),
        "subsets.json": json_bytes({"_header": header, **subsets}),
        "season_summary.json": json_bytes({"_header": header, "seasons": contest_summary(contests, orientations),
                                           "schedule_reconciliation_states": _count(schedule, "season", "state"),
                                           "cfbd_route_conflicts": {str(k): v for k, v in route_conflicts.items()},
                                           "bat652_spine_identity_diff": spine}),
    }
    inputs = {"cfbd_fbs_route": contract["input_bindings"]["cfbd_fbs_route"],
              "cfbd_fcs_route": contract["input_bindings"]["cfbd_fcs_route"],
              "bat652_spine_membership": contract["input_bindings"]["bat652_spine_membership"]["sha256"]}
    result = materialize(canonical_root=canonical_root, manifest_root=manifest_root, stage="contest",
                         contract_sha256=contract_sha256, inputs=inputs,
                         upstream={"program-season": m1_manifest["identity"]}, files=files,
                         manifest_extra={"issued_at_utc": issued_at_utc, "label": "BAT-710 national contest population",
                                         "row_counts": {"contests": len(contests), "orientations": len(orientations),
                                                        "schedule_reconciliation": len(schedule)}})
    return {**result, "row_counts": {"contests": len(contests), "orientations": len(orientations)}}


def bat652_spine_diff(contract: dict[str, Any], data_root: Path, cells: list[dict[str, Any]],
                      bindings: list[dict[str, Any]]) -> dict[str, Any]:
    binding = contract["input_bindings"]["bat652_spine_membership"]
    path = Path(data_root) / binding["path"]
    if sha256_file(path) != binding["sha256"]:
        raise PopulationRefused("INPUT_HASH_MISMATCH", "BAT-652 spine membership")
    teams: dict[int, set[str]] = {}
    pairs: dict[int, int] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            season = int(row["season"])
            if season not in TWO_SOURCE_SEASONS:
                continue
            for key in ("home_canonical_team_id", "away_canonical_team_id"):
                teams.setdefault(season, set()).add(str(row[key]).rsplit(":", 1)[-1])
            pairs[season] = pairs.get(season, 0) + 1
    cfbd_to_org = {b["cfbd_team_id"]: b["org_id"] for b in bindings if b["cfbd_team_id"]}
    out = {}
    for season in TWO_SOURCE_SEASONS:
        di = {c["ncaa_org_id"] for c in cells if c["season"] == season and c["in_division_i_population"] is True and c["ncaa_org_id"]}
        spine_orgs = {cfbd_to_org[t] for t in teams.get(season, set()) if t in cfbd_to_org}
        unbound = sorted(t for t in teams.get(season, set()) if t not in cfbd_to_org)
        out[str(season)] = {"spine_games": pairs.get(season, 0), "spine_teams": len(teams.get(season, set())),
                            "spine_teams_bound": len(spine_orgs), "spine_teams_unbound": unbound,
                            "spine_bound_not_division_i_here": sorted(spine_orgs - di),
                            "division_i_here_not_in_spine": len(di - spine_orgs)}
    return out


def run_query_db_stage(*, contract: dict[str, Any], contract_sha256: str, contest_manifest: Path, canonical_root: Path,
                       manifest_root: Path, issued_at_utc: str, repo_root: Path, write_gates: bool = True) -> dict[str, Any]:
    m2_manifest = load_stage_manifest(contest_manifest, stage="contest", contract_sha256=contract_sha256)
    m1_identity = m2_manifest["manifest"]["identity_document"]["upstream"]["program-season"]
    m1_path = Path(manifest_root) / "sha256" / m1_identity / "run_manifest.json"
    m1_manifest = load_stage_manifest(m1_path, stage="program-season", contract_sha256=contract_sha256)
    m1 = read_stage_outputs(m1_manifest, ["program_season_cells.jsonl.gz", "season_summary.json"])
    m2 = read_stage_outputs(m2_manifest, ["contests.jsonl.gz", "orientations.jsonl.gz", "subsets.json",
                                          "schedule_reconciliation.jsonl.gz", "season_summary.json"])
    database = build_query_database(contract_sha256=contract_sha256, m1_identity=m1_identity,
                                    m2_identity=m2_manifest["identity"], cells=m1["program_season_cells.jsonl.gz"],
                                    contests=m2["contests.jsonl.gz"], orientations=m2["orientations.jsonl.gz"],
                                    subsets=m2["subsets.json"], schedule=m2["schedule_reconciliation.jsonl.gz"])
    result = materialize(canonical_root=canonical_root, manifest_root=manifest_root, stage="query-db",
                         contract_sha256=contract_sha256, inputs={},
                         upstream={"program-season": m1_identity, "contest": m2_manifest["identity"]},
                         files={DB_FILE_NAME: database},
                         manifest_extra={"issued_at_utc": issued_at_utc, "label": "BAT-710 national population query database"})
    gates = None
    if write_gates:
        gates = write_successor_gates(repo_root=repo_root, contract=contract, contract_sha256=contract_sha256,
                                      m1_identity=m1_identity, m2_identity=m2_manifest["identity"],
                                      db_identity=result["identity"], m1=m1, m2=m2,
                                      m1_issued_at=m1_manifest["manifest"].get("issued_at_utc"))
    return {**result, "gates": gates}


DB_TABLES = {
    "program_season": ["cell_key", "season", "ncaa_org_id", "provider_key", "team_name", "ncaa_team_season_id",
                       "division_code_observed", "division_label", "division_authority", "header_record_wlt",
                       "disposition", "disposition_reason", "in_division_i_population", "transition_observed",
                       "transition_across_unobserved", "conference_official", "expected_sources", "observations",
                       "flags", "raw_sha256"],
    "contest": ["contest_key", "ncaa_contest_id", "season", "term", "contest_date", "site", "neutral_site_text",
                "contest_status", "competitive", "a_org_id", "a_team_season_id", "a_team_name", "a_division_label",
                "a_membership", "a_points", "b_org_id", "b_team_season_id", "b_team_name", "b_division_label",
                "b_membership", "b_points", "classification_pair", "mirror_observation_count", "source",
                "cfbd_game_ids", "reconciliation_state", "disposition", "disposition_reason", "exposure",
                "conflict_fields", "flags", "event_labels", "a_key", "b_key", "contest_dates_observed",
                "mirror_scores_observed", "contest_statuses_observed", "cfbd_observation"],
    "orientation": ["contest_key", "ncaa_contest_id", "season", "term", "contest_date", "side", "view", "team_membership",
                    "team_key", "opponent_key", "team_org_id",
                    "team_season_id", "team_name", "team_division_label", "opponent_org_id", "opponent_name",
                    "opponent_division_label", "site_for_team", "team_points", "opponent_points", "margin", "result",
                    "contest_status", "classification_pair", "disposition", "reconciliation_state", "exposure"],
    "schedule_reconciliation": ["cell_key", "season", "ncaa_org_id", "ncaa_team_season_id", "team_name",
                                "division_label", "page_rows", "contest_rows", "orientation_rows", "header_record",
                                "derived_record", "state"],
}


def _db_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


def build_query_database(*, contract_sha256: str, m1_identity: str, m2_identity: str, cells: list[dict[str, Any]],
                         contests: list[dict[str, Any]], orientations: list[dict[str, Any]], subsets: dict[str, Any],
                         schedule: list[dict[str, Any]]) -> bytes:
    """Deterministic in-memory SQLite, serialized to bytes (identical inputs give identical bytes)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA page_size=4096")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    for table, columns in DB_TABLES.items():
        conn.execute(f"CREATE TABLE {table} ({', '.join(columns)})")
    conn.execute("CREATE TABLE subset_membership (subset TEXT, contest_key TEXT)")
    for c in cells:
        row = dict(c)
        row["raw_sha256"] = (c.get("graph_page") or {}).get("raw_sha256")
        conn.execute(f"INSERT INTO program_season VALUES ({','.join('?' * len(DB_TABLES['program_season']))})",
                     [_db_value(row.get(k)) for k in DB_TABLES["program_season"]])
    for table, rows in (("contest", contests), ("orientation", orientations), ("schedule_reconciliation", schedule)):
        conn.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(DB_TABLES[table]))})",
                         [[_db_value(r.get(k)) for k in DB_TABLES[table]] for r in rows])
    for name in ("FBS_ESTIMAND_SUBSET", "FCS_SUBSET"):
        conn.executemany("INSERT INTO subset_membership VALUES (?, ?)", [(name, k) for k in subsets[name]])
    conn.executescript("""
        CREATE INDEX ix_ps_season ON program_season (season, ncaa_org_id);
        CREATE INDEX ix_contest_season ON contest (season, contest_date);
        CREATE INDEX ix_orient_season ON orientation (season, team_org_id);
    """)
    meta = {"schema_version": DB_SCHEMA_VERSION, "contract_sha256": contract_sha256, "program_season_identity": m1_identity,
            "contest_identity": m2_identity, "delivery_seasons": json.dumps(list(DELIVERY_SEASONS)),
            "single_source_seasons": json.dumps(list(SINGLE_SOURCE_SEASONS)),
            "non_claims": "no PIT, no predictive skill, no strength comparability, no pre-2016/2026 completeness, no scientific trust"}
    conn.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
    conn.commit()
    data = conn.serialize()
    conn.close()
    return bytes(data)


GATE_DIR_SI = "artifacts/scientific_integrity/cycle38"
GATE_DATA_LAKE = "artifacts/data_lake/national_di_population_2016_2025_gate.json"


def write_successor_gates(*, repo_root: Path, contract: dict[str, Any], contract_sha256: str, m1_identity: str,
                          m2_identity: str, db_identity: str, m1: dict[str, Any], m2: dict[str, Any],
                          m1_issued_at: str | None) -> dict[str, Any]:
    """New successor gate files (create-only); predecessors are only hashed, never written."""
    repo_root = Path(repo_root)
    predecessors = contract["successor_gates"]["predecessors_byte_unchanged"]
    for rel, sha in predecessors.items():
        if sha256_file(repo_root / rel) != sha:
            raise PopulationRefused("PREDECESSOR_CHANGED", rel)
    identities = {"contract_sha256": contract_sha256, "program_season": m1_identity, "contest": m2_identity,
                  "query_db": db_identity, "first_output_issued_at_utc": m1_issued_at}
    common = {"jira_key": "BAT-710", "cycle_number": 38, "attempt_number": 1, "identities": identities,
              "scope": "HISTORICAL_NATIONAL 2016-2025 program-seasons; contests 2016-2025, reconciled 2016-2023 only",
              "historical_audit_unit": "HT38-NATIONAL-DI-CONTEST-2016-2025", "new_pre_2016_units": 0,
              "single_source_2024_2025": {"reconciliation_state": SINGLE_SOURCE, "exposure": EXPOSURE_2024_2025},
              "non_claims": contract["non_claims"], "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
              "state": "PARTIAL_TRANCHE_RECONCILED_2016_2023_SINGLE_SOURCE_2024_2025"}
    contests = m2["contests.jsonl.gz"]
    pairs = {str(s): _count([c for c in contests if c["season"] == s], "classification_pair") for s in DELIVERY_SEASONS}
    gates = {
        f"{GATE_DIR_SI}/HISTORICAL_NATIONAL_PROGRAM_SEASON_POPULATION_2016_2025.json": {
            **common, "artifact_type": "HISTORICAL_NATIONAL_PROGRAM_SEASON_POPULATION_2016_2025",
            "predecessor": {"path": "artifacts/scientific_integrity/cycle29/HISTORICAL_NATIONAL_PROGRAM_SEASON_SCOPE_CONTRACT.json",
                            "sha256": predecessors["artifacts/scientific_integrity/cycle29/HISTORICAL_NATIONAL_PROGRAM_SEASON_SCOPE_CONTRACT.json"]},
            "membership_evidence_state": "OFFICIAL_GRAPH_DECODED_2016_2025_WITH_EXPLICIT_UNRESOLVED_CELLS",
            "seasons": m1["season_summary.json"]["seasons"]},
        f"{GATE_DIR_SI}/HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE_2016_2025.json": {
            **common, "artifact_type": "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE_2016_2025",
            "predecessor": {"path": "artifacts/scientific_integrity/cycle29/HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json",
                            "sha256": predecessors["artifacts/scientific_integrity/cycle29/HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json"]},
            "pair_counts_by_season": pairs},
        f"{GATE_DIR_SI}/HISTORICAL_FCS_GAME_ACQUISITION_AND_RECONCILIATION_GATE_2016_2025.json": {
            **common, "artifact_type": "HISTORICAL_FCS_GAME_ACQUISITION_AND_RECONCILIATION_GATE_2016_2025",
            "predecessor": {"path": "artifacts/scientific_integrity/cycle29/HISTORICAL_FCS_GAME_ACQUISITION_AND_RECONCILIATION_GATE.json",
                            "sha256": predecessors["artifacts/scientific_integrity/cycle29/HISTORICAL_FCS_GAME_ACQUISITION_AND_RECONCILIATION_GATE.json"]},
            "contests_by_season": m2["season_summary.json"]["seasons"]},
        f"{GATE_DIR_SI}/FCS_SUBSET_FROM_PARENT_2016_2025.json": {
            **common, "artifact_type": "FCS_AND_FBS_ESTIMAND_SUBSETS_FROM_PARENT_2016_2025",
            "predecessors": [{"path": "artifacts/scientific_integrity/cycle30/FCS_SUBSET_FROM_PARENT_SUMMARY.json",
                              "sha256": predecessors["artifacts/scientific_integrity/cycle30/FCS_SUBSET_FROM_PARENT_SUMMARY.json"]},
                             {"path": "artifacts/scientific_integrity/cycle29/PIT_KERNEL_POPULATION_SCOPE_AND_SUBDIVISION_GATE.json",
                              "sha256": predecessors["artifacts/scientific_integrity/cycle29/PIT_KERNEL_POPULATION_SCOPE_AND_SUBDIVISION_GATE.json"]},
                             {"path": contract["input_bindings"]["fcs_expected_game_population_predecessor"]["path"],
                              "sha256": contract["input_bindings"]["fcs_expected_game_population_predecessor"]["sha256"]}],
            "rules": m2["subsets.json"]["rules"], "proof": m2["subsets.json"]["proof"],
            "subset_identity": stable_hash({k: m2["subsets.json"][k] for k in ("FBS_ESTIMAND_SUBSET", "FCS_SUBSET")}),
            "manager_semantic_join_still_required": True},
        GATE_DATA_LAKE: {
            **common, "artifact_type": "NATIONAL_DI_POPULATION_2016_2025_GATE",
            "predecessor": {"path": "artifacts/data_lake/national_tiered_game_spine_gate.json",
                            "sha256": predecessors["artifacts/data_lake/national_tiered_game_spine_gate.json"]},
            "lake_roots": {"canonical": f"canonical/{POPULATION}/sha256/<identity>", "manifests": f"manifests/{POPULATION}/sha256/<identity>"}},
    }
    written = {}
    for rel, doc in gates.items():
        payload = json_bytes(doc)
        target = repo_root / rel
        if target.exists():
            if target.read_bytes() != payload:
                raise PopulationRefused("IMMUTABLE_COLLISION", f"{rel} exists with different bytes")
            written[rel] = {"sha256": sha256_bytes(payload), "state": "ALREADY_PRESENT_IDENTICAL"}
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(payload)
        written[rel] = {"sha256": sha256_bytes(payload), "state": "WRITTEN"}
    return written
