"""Bind person and role to the same staff record with declared coordinates.

Page-wide independent name and title hits are STRING_LOCATED only.
CONFIRMED requires PERSON_RECORD_BOUND and ROLE_CLAIM_SUPPORTED.
Unescaped offsets are never presented as raw-html offsets.
"""

from __future__ import annotations

import hashlib
import html as html_lib
import re
from functools import lru_cache
from typing import Any, Mapping

from aggie_analytics.cycle30.coaching import parse_official_staff_html
from aggie_analytics.cycle33.role_taxonomy import principal_role_families

PARSER_VERSION = "BAS-STAFF-SPAN-SAME-RECORD-v33.3"
COORD_RAW = "raw_html"
COORD_UNESCAPED = "html_unescaped"
COORD_BR_NORMALIZED = "html_br_normalized"

_APOSTROPHE = dict.fromkeys("’‘‛`", "'")
_JR = re.compile(r",?\s*jr\.?\s*$", re.I)
_TR = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
_CELL = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.I | re.S)
_BLOCK = re.compile(
    r"<(p|div|li|h[1-6]|span|td|th)\b[^>]*>(.*?)</\1>",
    re.I | re.S,
)
_TAG = re.compile(r"<[^>]+>")
_BR = re.compile(r"<br\s*/?>", re.I)
# Double quotes only. Apostrophes are part of names far more often than they
# delimit nicknames -- `Ka'imi O'Brien` contains two of them, and treating
# them as delimiters would strip the middle of a real person's name.
_QUOTED_NICKNAME = re.compile("[\"“”]{1}[^\"“”]{1,40}[\"“”]{1}")
_TITLE_HINT = re.compile(
    r"\b(?:coach|coordinator|analyst|director|manager|assistant|"
    r"associate|special teams|quality control|recruiting|"
    r"strength|operations|specialist)\b",
    re.I,
)


def _variants(text: str) -> tuple[str, ...]:
    raw = str(text or "").strip()
    if not raw:
        return ()
    unesc = html_lib.unescape(raw).replace("\xa0", " ")
    folded = unesc.translate(str.maketrans(_APOSTROPHE))
    collapsed = re.sub(r"\s+", " ", folded)
    values = [raw, unesc, folded, collapsed, _JR.sub("", collapsed).strip()]
    # A sourced quoted nickname is a legitimate alias form: the same person
    # may be published as `Deion "Coach Prime" Sanders` on one page and
    # `Deion Sanders` on another. Both spellings are offered so the pair can
    # match, without the substring fallback this repair removed.
    nickname_free = _QUOTED_NICKNAME.sub(" ", collapsed)
    nickname_free = re.sub(r"\s+", " ", nickname_free).strip()
    if nickname_free and nickname_free != collapsed:
        values.append(nickname_free)
    recruits = re.split(r"\brecruits\s*:", collapsed, maxsplit=1, flags=re.I)
    if len(recruits) == 2:
        values.append(recruits[0].strip().rstrip("/,-"))
    if "coordinator" in collapsed.casefold() and "/" not in collapsed:
        values.append(
            re.sub(r"(coordinator)\s+", r"\1 / ", collapsed, flags=re.I).strip()
        )
    if "," in collapsed:
        last, _, first = collapsed.partition(",")
        swapped = f"{first.strip()} {last.strip()}".strip()
        if first.strip() and last.strip():
            values.append(swapped)
    return tuple(dict.fromkeys(item for item in values if item))


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(str(text or "")).strip()).casefold()


def _unescape_map(raw: str) -> tuple[str, list[int]]:
    """Return unescaped text and a map from decoded index -> raw start index."""

    out: list[str] = []
    raw_at: list[int] = []
    i = 0
    n = len(raw)
    while i < n:
        if raw[i] == "&":
            semi = raw.find(";", i + 1, i + 48)
            if semi > i:
                entity = raw[i : semi + 1]
                decoded = html_lib.unescape(entity)
                if decoded != entity:
                    for _ch in decoded:
                        out.append(_ch)
                        raw_at.append(i)
                    i = semi + 1
                    continue
        ch = " " if raw[i] == "\xa0" else raw[i]
        out.append(ch)
        raw_at.append(i)
        i += 1
    return "".join(out), raw_at


def _br_map(raw: str) -> tuple[str, list[int]]:
    out: list[str] = []
    raw_at: list[int] = []
    last = 0
    for match in _BR.finditer(raw):
        for idx in range(last, match.start()):
            out.append(raw[idx])
            raw_at.append(idx)
        out.append(" ")
        raw_at.append(match.start())
        last = match.end()
    for idx in range(last, len(raw)):
        out.append(raw[idx])
        raw_at.append(idx)
    return "".join(out), raw_at


def _find(body: str, needle: str) -> int:
    if not needle:
        return -1
    idx = body.find(needle)
    if idx >= 0:
        return idx
    idx = body.casefold().find(needle.casefold())
    if idx >= 0:
        return idx
    parts = [part for part in re.split(r"\s+", needle.strip()) if part]
    if len(parts) < 2:
        return -1
    pattern = re.compile(r"\s+".join(re.escape(part) for part in parts), re.I)
    found = pattern.search(body)
    return found.start() if found else -1


def _search_with_map(
    original: str, needle: str, haystack: str, raw_at: list[int], system: str
) -> dict[str, Any] | None:
    for variant in _variants(needle):
        idx = _find(haystack, variant)
        if idx < 0:
            continue
        end = idx + max(len(variant), 1)
        if raw_at:
            raw_start = raw_at[idx] if idx < len(raw_at) else idx
            raw_end = raw_at[min(end, len(raw_at) - 1)] + 1 if raw_at else end
        else:
            raw_start, raw_end = idx, end
        return {
            "coordinate_system": COORD_RAW,
            "body_offset": raw_start,
            "body_end_offset": raw_end,
            "evidence_text": original[raw_start:raw_end],
            "match_system": system,
            "decoded_offset": idx if system != COORD_RAW else None,
            "decoded_end_offset": end if system != COORD_RAW else None,
            "variant": variant,
        }
    return None


def locate_string(html: str, needle: str) -> dict[str, Any] | None:
    """Locate a string and report a raw-html interval plus any transform map."""

    body = html or ""
    unescaped, unesc_map = _unescape_map(body)
    br_norm, br_map = _br_map(body)
    searches = (
        (body, list(range(len(body))), COORD_RAW),
        (unescaped, unesc_map, COORD_UNESCAPED),
        (br_norm, br_map, COORD_BR_NORMALIZED),
    )
    for haystack, raw_at, system in searches:
        found = _search_with_map(body, needle, haystack, raw_at, system)
        if found is not None:
            found["transformations"] = [
                item
                for item in (
                    "html.unescape" if system == COORD_UNESCAPED else None,
                    "br_to_space" if system == COORD_BR_NORMALIZED else None,
                )
                if item
            ]
            return found
    return None


def _plain(html: str) -> str:
    text = html_lib.unescape(_BR.sub(" ", html or ""))
    text = _TAG.sub(" ", text)
    return re.sub(r"\s+", " ", text).replace("\xa0", " ").strip()


def _looks_like_title(text: str) -> bool:
    return bool(_TITLE_HINT.search(text or ""))


_NAME_TOKEN = re.compile(r"[0-9a-z]+", re.I)


def _name_tokens(text: str) -> tuple[str, ...]:
    """Lowercase word tokens, punctuation-stripped. `J.R. Smith` -> (jr, smith)."""

    return tuple(match.group(0).casefold() for match in _NAME_TOKEN.finditer(text or ""))


def _token_subsequence_at_boundary(needle: tuple[str, ...], hay: tuple[str, ...]) -> bool:
    """True when `needle` appears in `hay` as CONSECUTIVE WHOLE tokens.

    This is the difference between identity and coincidence. Substring
    containment says "john smith" is inside "john smithson"; whole-token
    matching says the second token is `smithson`, which is not `smith`, so
    they are different people. Word boundaries are the entire point.
    """

    if not needle or len(needle) > len(hay):
        return False
    first = needle[0]
    for start in range(len(hay) - len(needle) + 1):
        if hay[start] != first:
            continue
        if hay[start : start + len(needle)] == needle:
            return True
    return False


def _name_match(person: str, candidate: str) -> bool:
    """Same-person identity between a claimed name and a candidate string.

    MR34-03 repair. The previous final clause was
    `any(item in _fold(candidate) for item in left)` -- raw substring
    containment, which confirmed `John Smith` from a record reading
    `John Smithson Head Coach`. Surname prefixes are extremely common
    (Smith/Smithson, Brown/Browne, Will/Williams, Stew/Stewart), so this was
    not a rare collision.

    The variant-equality path is kept unchanged: it is what legitimately
    resolves sourced aliases and orderings (`Smith, John` -> `John Smith`,
    `Jr.` suffixes, curly apostrophes, `&nbsp;`). What replaces the substring
    fallback is whole-token sequence matching, so a longer record name still
    matches a shorter claimed name only when every claimed token is present
    as a complete token, in order -- `John Smith` matches
    `John Smith Head Coach` and `John Smith Jr.`, but never `John Smithson`.
    """

    left = {_fold(item) for item in _variants(person) if item}
    right = {_fold(item) for item in _variants(candidate) if item}
    if left and right and (left & right):
        return True
    hay = _name_tokens(candidate)
    if not hay:
        return False
    for variant in _variants(person):
        needle = _name_tokens(variant)
        # A single token is a given name or a surname alone; it is not an
        # identity, and matching on it is how unrelated staff collide.
        if len(needle) < 2:
            continue
        if _token_subsequence_at_boundary(needle, hay):
            return True
    return False


def _variant_equal(left: str, right: str) -> bool:
    a = {_fold(item) for item in _variants(left) if item}
    b = {_fold(item) for item in _variants(right) if item}
    return bool(a and b and (a & b))


def role_claim_supported_on_title(record_title: str, claimed_title: str) -> bool:
    """True when the claimed title/role is supported by the same-record title."""

    claimed = str(claimed_title or "").strip()
    record = str(record_title or "").strip()
    if not claimed or not record:
        return False
    if _variant_equal(record, claimed):
        return True
    claimed_families = set(principal_role_families(claimed))
    record_families = set(principal_role_families(record))
    if claimed_families:
        return bool(claimed_families <= record_families)
    record_fold = _fold(record)
    for variant in _variants(claimed):
        folded = _fold(variant)
        if folded and folded in record_fold:
            return True
    return False


def _table_records(html: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for ordinal, match in enumerate(_TR.finditer(html or "")):
        inner = match.group(1)
        inner_origin = match.start(1)
        cells: list[dict[str, Any]] = []
        for cell in _CELL.finditer(inner):
            raw_cell = cell.group(1)
            cells.append(
                {
                    "text": _plain(raw_cell),
                    "start": inner_origin + cell.start(1),
                    "end": inner_origin + cell.end(1),
                    "raw": raw_cell,
                }
            )
        if len(cells) < 2:
            continue
        person_cell = next((cell for cell in cells if cell["text"]), None)
        if person_cell is None:
            continue
        if not _name_like(person_cell["text"]):
            continue
        title_cell = next(
            (
                cell
                for cell in cells
                if cell is not person_cell and _looks_like_title(cell["text"])
            ),
            None,
        )
        if title_cell is None:
            title_cell = next(
                (cell for cell in cells if cell is not person_cell and cell["text"]),
                None,
            )
        if title_cell is None:
            continue
        records.append(
            {
                "kind": "table_row",
                "selector": f"tr[{ordinal}]",
                "person": person_cell["text"],
                "title": title_cell["text"],
                "person_start": person_cell["start"],
                "person_end": person_cell["end"],
                "title_start": title_cell["start"],
                "title_end": title_cell["end"],
                "record_html": match.group(0),
            }
        )
    return records


def _block_pair_records(html: str) -> list[dict[str, Any]]:
    # Nested-tag regex on full official pages is not a staff parser.
    if len(html or "") > 8_000:
        return []
    blocks = list(_BLOCK.finditer(html or ""))
    records: list[dict[str, Any]] = []
    for idx, match in enumerate(blocks):
        text = _plain(match.group(2))
        if not text:
            continue
        nxt = blocks[idx + 1] if idx + 1 < len(blocks) else None
        if nxt is None:
            continue
        nxt_text = _plain(nxt.group(2))
        if _looks_like_title(text) or not nxt_text:
            continue
        if _looks_like_title(nxt_text) or _name_like(text):
            if _name_like(text) and (_looks_like_title(nxt_text) or nxt_text):
                records.append(
                    {
                        "kind": "adjacent_blocks",
                        "selector": f"{match.group(1)}[{idx}]+{nxt.group(1)}",
                        "person": text,
                        "title": nxt_text,
                        "person_start": match.start(2),
                        "person_end": match.end(2),
                        "title_start": nxt.start(2),
                        "title_end": nxt.end(2),
                        "record_html": html[match.start() : nxt.end()],
                    }
                )
    return records


def strip_quoted_nickname(text: str) -> str:
    """Remove a quoted nickname segment from a sourced personal name.

    R35-02, defect found by the 880-row reparse: `Deion "Coach Prime"
    Sanders` was not treated as a name at all, because `_looks_like_title`
    matched the word `Coach` INSIDE the nickname and classified the whole
    cell as a title. The staff row was therefore never extracted, and a real,
    correctly sourced head-coach appointment silently disappeared from the
    record set.

    Only quote-delimited segments are removed. Parentheses are left alone --
    they carry disambiguating information (`Miami (OH)`) rather than
    nicknames, and stripping them would trade one identity bug for another.
    """

    stripped = _QUOTED_NICKNAME.sub(" ", str(text or ""))
    return re.sub(r"\s+", " ", stripped).strip()


def _name_like(text: str) -> bool:
    folded = _fold(text)
    # A title word inside a quoted nickname is part of the person's name, not
    # a job title, so the title test runs against the nickname-stripped form.
    if not folded or _looks_like_title(strip_quoted_nickname(text)):
        return False
    if re.fullmatch(r"\d{4}", folded):
        return False
    if not re.search(r"[a-z]", folded):
        return False
    parts = [part for part in re.split(r"[^\w.]+", folded) if part]
    return 1 <= len(parts) <= 6


def _single_statement_record(html: str) -> list[dict[str, Any]]:
    if _TR.search(html or ""):
        return []
    plain = _plain(html or "")
    if not plain or len(plain) > 400:
        return []
    return [
        {
            "kind": "biography_statement",
            "selector": "document_text",
            "person": plain,
            "title": plain,
            "person_start": 0,
            "person_end": len(html or ""),
            "title_start": 0,
            "title_end": len(html or ""),
            "record_html": html,
        }
    ]


def _official_parser_records(html: str) -> list[dict[str, Any]]:
    try:
        nodes = parse_official_staff_html(
            html, page_url="local://span-bind", program_name=None
        )
    except (TypeError, ValueError):
        return []
    records: list[dict[str, Any]] = []
    for node in nodes or []:
        person = str(node.get("person") or "")
        title = str(node.get("title") or node.get("source_title") or "")
        if not person:
            continue
        start = node.get("body_offset")
        try:
            start_i = int(start)
        except (TypeError, ValueError):
            start_i = 0
        records.append(
            {
                "kind": "official_html_parser",
                "selector": str(node.get("span_id") or "official_parser"),
                "person": person,
                "title": title,
                "person_start": start_i,
                "person_end": start_i + len(person),
                "title_start": start_i,
                "title_end": start_i + len(title),
                "record_html": f"{person} {title}",
            }
        )
    return records


def iter_staff_records(html: str) -> list[dict[str, Any]]:
    """Attributed staff records: table rows, official parser, or short statements."""

    return list(_iter_staff_records_cached(html))


_BIO_H1 = re.compile(
    r'<h1\b[^>]*class="[^"]*roster-bio-main-info__title[^"]*"[^>]*>(.*?)</h1>',
    re.I | re.S,
)
_BIO_POS = re.compile(
    r'<strong\b[^>]*class="[^"]*roster-bio-main-info__position[^"]*"[^>]*>(.*?)</strong>',
    re.I | re.S,
)
_BIO_TITLE_FIELD = re.compile(
    r'roster-bio-meta__profile-field-label">\s*Title\s*</small>\s*'
    r'<span\b[^>]*class="[^"]*roster-bio-meta__profile-field-value[^"]*"[^>]*>'
    r"(.*?)</span>",
    re.I | re.S,
)


def _staff_bio_records(html: str) -> list[dict[str, Any]]:
    """Sidearm roster-bio subject card: H1 plus current Title/position only."""

    body = html or ""
    if "roster-bio" not in body.casefold():
        return []
    records: list[dict[str, Any]] = []
    title_field = _BIO_TITLE_FIELD.search(body)
    field_title = _plain(title_field.group(1)) if title_field else ""
    for match in _BIO_H1.finditer(body):
        person = _plain(match.group(1))
        if not person:
            continue
        window = body[match.end() : match.end() + 1500]
        pos = _BIO_POS.search(window)
        title = _plain(pos.group(1) if pos else "") or field_title
        if not title:
            continue
        title_start = (
            match.end() + pos.start(1)
            if pos is not None
            else (title_field.start(1) if title_field else match.start(1))
        )
        title_end = (
            match.end() + pos.end(1)
            if pos is not None
            else (title_field.end(1) if title_field else match.end(1))
        )
        records.append(
            {
                "kind": "staff_bio_card",
                "selector": "h1.roster-bio-main-info__title+position",
                "person": person,
                "title": title,
                "person_start": match.start(1),
                "person_end": match.end(1),
                "title_start": title_start,
                "title_end": title_end,
                "record_html": body[match.start() : title_end],
            }
        )
    if records:
        return records
    if field_title:
        title_tag = re.search(r"<title>(.*?)</title>", body, re.I | re.S)
        person = (
            _plain(title_tag.group(1)).split("-", 1)[0].strip() if title_tag else ""
        )
        if person and field_title:
            records.append(
                {
                    "kind": "staff_bio_card",
                    "selector": "title+roster-bio-meta__profile-field-value",
                    "person": person,
                    "title": field_title,
                    "person_start": title_tag.start(1) if title_tag else 0,
                    "person_end": title_tag.end(1) if title_tag else 0,
                    "title_start": title_field.start(1) if title_field else 0,
                    "title_end": title_field.end(1) if title_field else 0,
                    "record_html": f"{person} {field_title}",
                }
            )
    return records


@lru_cache(maxsize=256)
def _iter_staff_records_cached(html: str) -> tuple[dict[str, Any], ...]:
    bio = _staff_bio_records(html)
    structured = _table_records(html)
    if bio:
        return tuple(bio + structured)
    if structured:
        return tuple(structured)
    official = _official_parser_records(html)
    if official:
        return tuple(official)
    pairs = _block_pair_records(html)
    if pairs:
        return tuple(pairs)
    return tuple(_single_statement_record(html))


def bind_person_role(html: str, *, person: str, title: str = "") -> dict[str, Any]:
    """Separate string location from same-record person/role support."""

    body = html or ""
    source_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    person_hit = locate_string(body, person) if str(person or "").strip() else None
    title_hit = locate_string(body, title) if str(title or "").strip() else None
    string_located = person_hit is not None and (
        not str(title or "").strip() or title_hit is not None
    )
    records = iter_staff_records(body)
    bound: dict[str, Any] | None = None
    contrary: list[dict[str, Any]] = []
    for record in records:
        if not _name_match(person, record["person"]) and not _name_match(
            person, _plain(record.get("record_html") or "")
        ):
            if str(title or "").strip() and role_claim_supported_on_title(
                record["title"], title
            ):
                contrary.append(
                    {
                        "person": record["person"],
                        "title": record["title"],
                        "selector": record["selector"],
                        "reason": "TITLE_ON_DIFFERENT_PERSON_RECORD",
                    }
                )
            continue
        bound = record
        break
    person_record_bound = bound is not None
    claimed = str(title or "").strip()
    role_supported = False
    reject_reason = None
    if not claimed:
        reject_reason = "EMPTY_TITLE_NAME_OBSERVATION_ONLY"
    elif bound is None:
        reject_reason = "PERSON_NOT_BOUND_TO_STAFF_RECORD"
    else:
        role_supported = role_claim_supported_on_title(bound["title"], claimed)
        if not role_supported:
            reject_reason = "ROLE_NOT_ON_SAME_RECORD"
    coordinate = {
        "coordinate_system": COORD_RAW,
        "parser_version": PARSER_VERSION,
        "source_hash_sha256": source_hash,
        # MR33-15 repair: `source_hash_sha256` is NOT a hash of the original
        # file's raw bytes -- `html` arrives here as an already-decoded
        # Python str (the caller read it in text mode, which applies
        # universal-newline translation \r\n/\r -> \n by default), and this
        # hash is sha256(html.encode("utf-8")) of THAT decoded/normalized
        # string. Calling it "raw" without qualification is exactly the
        # ambiguity the finding flagged (880 source-text hashes matched
        # under this normalized representation; only 495 equal the original
        # file bytes). Made explicit and unambiguous here rather than
        # inferred by a consumer.
        "source_hash_sha256_representation": "SHA256_OF_UTF8_ENCODED_UNIVERSAL_NEWLINE_DECODED_TEXT",
        "source_hash_sha256_equals_original_file_bytes": False,
        # Named distinctly from the pre-existing `transformations` key (which
        # describes person/title record-text transformations, e.g.
        # html_unescape) so this addition cannot silently clobber that
        # unrelated field when both are merged into the same result dict.
        "source_hash_transformations": ["universal_newline_decode", "utf8_encode_for_hash"],
        "transformations_declared": True,
    }
    person_interval = person_hit or {}
    title_interval = title_hit or {}
    if bound is not None:
        person_interval = {
            "coordinate_system": COORD_RAW,
            "body_offset": bound["person_start"],
            "body_end_offset": bound.get("person_end")
            or bound["person_start"] + len(bound.get("person") or ""),
            "evidence_text": body[
                bound["person_start"] : bound.get("person_end")
                or bound["person_start"] + len(bound.get("person") or "")
            ],
            "transformations": ["html_unescape_for_record_text"],
            "match_system": COORD_RAW,
            "record_plain_person": bound["person"],
        }
        if claimed:
            title_interval = {
                "coordinate_system": COORD_RAW,
                "body_offset": bound["title_start"],
                "body_end_offset": bound.get("title_end")
                or bound["title_start"] + len(bound.get("title") or ""),
                "evidence_text": body[
                    bound["title_start"] : bound.get("title_end")
                    or bound["title_start"] + len(bound.get("title") or "")
                ],
                "transformations": ["html_unescape_for_record_text"],
                "match_system": COORD_RAW,
                "record_plain_title": bound["title"],
            }
    return {
        "string_located": string_located,
        "person_record_bound": person_record_bound,
        "role_claim_supported": role_supported,
        "locatable": role_supported,
        "name_observation_only": person_record_bound and not claimed,
        "body_offset": (person_interval or {}).get("body_offset"),
        "body_end_offset": (person_interval or {}).get("body_end_offset"),
        "title_offset": (title_interval or {}).get("body_offset"),
        "title_end_offset": (title_interval or {}).get("body_end_offset"),
        "coordinate_system": COORD_RAW,
        "evidence_text": (person_interval or {}).get("evidence_text"),
        "title_evidence_text": (title_interval or {}).get("evidence_text"),
        "transformations": (person_interval or {}).get("transformations") or [],
        "person_interval": person_interval,
        "title_interval": title_interval,
        "record_selector": None if bound is None else bound.get("selector"),
        "record_kind": None if bound is None else bound.get("kind"),
        "record_title": None if bound is None else bound.get("title"),
        "record_person": None if bound is None else bound.get("person"),
        "contrary_records": contrary,
        "reject_reason": reject_reason,
        "span_id_string_built_insufficient": True,
        "parser_version": PARSER_VERSION,
        "source_hash_sha256": source_hash,
        "pit_admitted": False,
        "confirmed_not_from_locatable_alone": True,
        **coordinate,
    }


def locate_person_title(html: str, *, person: str, title: str = "") -> dict[str, Any]:
    """Compatibility wrapper. locatable means same-record role support."""

    return bind_person_role(html, person=person, title=title)


def person_matches_record(person: str, record: Mapping[str, Any]) -> bool:
    return _name_match(person, str(record.get("person") or ""))
