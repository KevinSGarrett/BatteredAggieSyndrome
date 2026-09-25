r"""Cycle #37 — Attempt #5 — an explicitly selected career successor over a delivered national release.

TP37-A04-06 / R37A04-06, extended by TP37-A05-02/06 (R37A05-02, R37A05-06). The delivered release
(``CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite``, SHA-256 ``757d4b5f...``) keeps its bytes, its default path and its
answers. A correction of its career rows is delivered as a *separate*, read-only successor file that a consumer
selects only by naming it (``bas-staff-query --career-successor <file>``); nothing here makes one a default.

Two successor formats are read:

* ``BAS-C37A04-CAREER-SUCCESSOR-FORMAT-v1`` (Attempt 4): ``successor_identity``, ``career_episode_a04`` (every
  episode under a ``C37A04:`` identity, each naming the predecessor rows it derives from) and
  ``career_a04_disposition`` (exactly one row per predecessor episode);
* ``BAS-C37A05-CAREER-SUCCESSOR-FORMAT-v1`` (Attempt 5): the same over ``career_episode_a05`` /
  ``career_a05_disposition`` under ``C37A05:`` identities, plus ``career_a05_from_a04`` -- exactly one row per
  Attempt 4 episode, naming the Attempt 5 rows it became -- so original, Attempt 4 and Attempt 5 identities are all
  conserved.

What :func:`attach_successor` proves before a query reads a row (MF37A04-02). Attempt 4 checked the file digest,
the declared ledgers and identity coverage, but the ledgers are the successor's own statements: the Attempt 4
manager deleted a referenced row, re-hashed the ledgers, pinned the new digest and was served, with a disposition
left dangling. A digest pin establishes *bytes*, not lineage. So, independently of every self-declared hash:

* identities are unique, lie in their versioned namespace and agree with the row's own page, revision, family,
  row and interval;
* the disposition covers exactly the open predecessor's episode set, once each;
* every successor identity a disposition names exists, and every predecessor identity an episode names exists;
* the predecessor-to-successor edges the dispositions state equal, edge for edge, the successor-to-predecessor
  edges the episodes state;
* each disposition is compatible with its edges (``NOT_PRODUCED`` has none, every other disposition has some),
  each episode's lineage state with its predecessors (a legitimately added row has none), and each episode's
  recorded disposition with the dispositions that name it;
* (Attempt 5 format) the Attempt 4 mapping has the same properties, covers the declared Attempt 4 row count, and
  -- where the declared Attempt 4 file is present with its declared digest -- exactly that file's identity set;
* every row names a raw revision file, its SHA-256 and the revision text's SHA-256.

Each failure has its own refusal code. At serve time :class:`RawBytesVerifier` re-reads every served row's raw
file: an absent file, changed bytes, a revision text that no longer hashes to the recorded digest, or a recorded
span whose text differs is refused; a row whose raw evidence is absent is refused, never labelled verified.

Cycle #37 -- Attempt #6 (MF37A05-01). Reciprocal edges and re-hashed ledgers are not lineage: the Attempt 5
manager swapped the predecessor edges of two different people's rows, both ways, re-hashed the ledgers and was
served; and replaced one row's raw capture, digests, text and spans with another person's genuine capture, under
the row's own page and revision, and was served. An edge is now a *typed semantic binding*, proved at attach for
every row and never from a self-declared hash alone:

* a predecessor identity names its own page, revision and family; a child row must carry the same page, revision
  and family, and the predecessor row's own raw locator (its capture's SHA-256 and its revision text's SHA-256)
  must equal the child's -- so a row that names another person's row, or carries another capture's evidence, is
  refused for that cause;
* every disposition's recorded predecessor-row digest is recomputed from the open predecessor's actual row;
* (Attempt 5 format) every Attempt 4 identity a row names carries the same page, revision and family, and, where
  the declared Attempt 4 file is present with its declared digest, that file's row carries the same raw locator and
  hashes to the mapping's recorded digest;
* at serve time the raw capture itself is opened and its own page id and revision id must be the row's; a valid
  capture of another page is refused whatever its digests say.

A display name is never an identity: two rows of the same person on different pages, or of different people who
share a name, are bound only through page, revision and family. Legitimately added rows (no predecessor), split
rows (one predecessor, several successors), rows without a team span, and typed other-sport or unknown employers
carry no binding these checks would refuse.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

# ---- Attempt 4 format (retained; the Attempt 4 builder and file still use these names) ----
FORMAT_VERSION = "BAS-C37A04-CAREER-SUCCESSOR-FORMAT-v1"
SUCCESSOR_VERSION = "BAS-C37A04-CAREER-SUCCESSOR-v1"
PREDECESSOR_TABLE = "career_episode_successor"
EPISODE_TABLE = "career_episode_a04"
DISPOSITION_TABLE = "career_a04_disposition"
IDENTITY_TABLE = "successor_identity"
SUCCESSOR_TABLES = (EPISODE_TABLE, DISPOSITION_TABLE)
ATTACHED_SCHEMA = "explicit_successor"
VIEW_NAME = "career_episode_explicit_successor"
IDENTITY_PREFIX = "C37A04"
NOT_ACTIVATED = "NOT_ACTIVATED"
NOT_ACCEPTED = "PRIVATE_WORKER_SUCCESSOR_NOT_ACCEPTED"
EVIDENCE_CLASS = "RETROSPECTIVE_SECONDARY_WIKIMEDIA_REVISION"

# ---- Attempt 5 format ----
A05_FORMAT_VERSION = "BAS-C37A05-CAREER-SUCCESSOR-FORMAT-v1"
A05_SUCCESSOR_VERSION = "BAS-C37A05-CAREER-SUCCESSOR-v1"
A05_EPISODE_TABLE = "career_episode_a05"
A05_DISPOSITION_TABLE = "career_a05_disposition"
A05_FROM_A04_TABLE = "career_a05_from_a04"
A05_IDENTITY_PREFIX = "C37A05"
SUPPORTED_SUCCESSOR_VERSIONS = frozenset({SUCCESSOR_VERSION, A05_SUCCESSOR_VERSION})

#: Dispositions of a predecessor episode (and, in the Attempt 5 format, of an Attempt 4 episode).
UNCHANGED = "UNCHANGED"
CORRECTED = "CORRECTED"
UNRESOLVED_EXPLICIT = "MADE_EXPLICITLY_UNRESOLVED"
RESTRUCTURED = "RESTRUCTURED_INTERVALS"
NOT_PRODUCED = "NOT_PRODUCED_BY_THE_SUCCESSOR_PARSER"
DISPOSITIONS = frozenset({UNCHANGED, CORRECTED, UNRESOLVED_EXPLICIT, RESTRUCTURED, NOT_PRODUCED})
DERIVED = "DERIVED_FROM_PREDECESSOR_ROWS"
#: The lineage states of an episode with no predecessor row, by format (legitimately added rows).
ADDED_STATES = {FORMAT_VERSION: "NEW_IN_A04_SUCCESSOR_NO_PREDECESSOR_ROW",
                A05_FORMAT_VERSION: "NEW_IN_A05_SUCCESSOR_NO_PREDECESSOR_ROW"}
A04_DERIVED = "DERIVED_FROM_A04_ROWS"
A04_ADDED = "NEW_IN_A05_NO_A04_ROW"

#: The predecessor columns, in the delivered table's order, carried unchanged in meaning by the successor.
PREDECESSOR_COLUMNS = (
    "assignments", "classification", "employer_display", "employer_kind", "employer_link_basis",
    "employer_link_target", "employer_qualifiers", "end", "episode_id", "evidence_class", "family",
    "homonym_display_name", "interval_index", "join", "ongoing", "page_title", "pageid", "parser_version",
    "person_display", "pit_admitted", "population_state", "raw_file", "raw_file_sha256", "resolution", "revision",
    "role_basis", "role_text", "row_index", "start", "team_byte_span", "team_char_span", "team_raw", "wikidata_qid",
    "wikitext_sha256", "years_as_written", "years_char_span", "years_raw",
)
#: What the successor adds to each row.
SUCCESSOR_COLUMNS = (
    "predecessor_episode_ids", "lineage_state", "start_state", "end_state", "start_bounds", "end_bounds",
    "start_qualifier", "end_qualifier", "definite_first_season", "definite_last_season", "possible_first_season",
    "possible_last_season", "bounds_consistent", "uncertainty_classes", "unresolved_parentheticals",
    "employer_qualifier_kinds", "role_parentheticals", "career_field", "disposition",
)
EPISODE_COLUMNS = PREDECESSOR_COLUMNS + SUCCESSOR_COLUMNS
#: What the Attempt 5 format adds: its Attempt 4 lineage, the date basis (own, or inherited with the parent's
#: raw locator) and the raw text of any date template it could not read.
A05_ADDED_COLUMNS = ("a04_episode_ids", "a04_lineage_state", "a04_disposition", "date_basis", "date_parent",
                     "unresolved_date_templates")
A05_EPISODE_COLUMNS = EPISODE_COLUMNS + A05_ADDED_COLUMNS
DISPOSITION_COLUMNS = ("predecessor_episode_id", "disposition", "successor_episode_ids", "changed_fields",
                       "predecessor_row_sha256", "screens", "reason")
A04_MAP_COLUMNS = ("a04_episode_id", "disposition", "a05_episode_ids", "changed_fields", "a04_row_sha256", "screens",
                   "reason")
#: JSON-encoded columns of the predecessor table; they are compared decoded, never as text.
PREDECESSOR_JSON_COLUMNS = frozenset({"assignments", "classification", "employer_qualifiers", "join", "resolution",
                                      "team_byte_span", "team_char_span", "years_char_span"})
#: Uncertainty classes a row can carry; each is retrievable through the consumer.
UNCERTAINTY_CLASSES = ("UNRESOLVED_ROLE", "UNKNOWN_START", "UNKNOWN_END", "UNCERTAIN_START", "UNCERTAIN_END",
                       "NO_DEFINITE_SEASON", "INCONSISTENT_BOUNDS", "UNRESOLVED_DATE_TEMPLATE")

REFUSED_ABSENT = "REFUSED_CAREER_SUCCESSOR_ABSENT"
REFUSED_NOT_A_SUCCESSOR = "REFUSED_CAREER_SUCCESSOR_TABLES_OR_IDENTITY_ABSENT"
REFUSED_VERSION = "REFUSED_CAREER_SUCCESSOR_VERSION_NOT_SUPPORTED"
REFUSED_PREDECESSOR = "REFUSED_CAREER_SUCCESSOR_PREDECESSOR_DIGEST_MISMATCH"
REFUSED_FILE_DIGEST = "REFUSED_CAREER_SUCCESSOR_FILE_DIGEST_MISMATCH"
REFUSED_LEDGER = "REFUSED_CAREER_SUCCESSOR_LEDGER_MISMATCH"
REFUSED_COVERAGE = "REFUSED_CAREER_SUCCESSOR_IDENTITY_COVERAGE"
REFUSED_ACTIVATION = "REFUSED_CAREER_SUCCESSOR_CLAIMS_ACTIVATION"
REFUSED_AUTHORITY = "REFUSED_CAREER_SUCCESSOR_CLAIMS_AUTHORITY_IT_DOES_NOT_HAVE"
REFUSED_RAW = "REFUSED_CAREER_SUCCESSOR_RAW_BYTES_CHANGED"
REFUSED_ROW_BINDING = "REFUSED_CAREER_SUCCESSOR_PREDECESSOR_ROW_BINDING_CHANGED"
# v37.5 (MF37A04-02): lineage and raw evidence proven independently of the successor's own ledgers.
REFUSED_INVALID_IDENTITY = "REFUSED_CAREER_SUCCESSOR_INVALID_IDENTITY"
REFUSED_MALFORMED_LINEAGE = "REFUSED_CAREER_SUCCESSOR_MALFORMED_LINEAGE"
REFUSED_DANGLING = "REFUSED_CAREER_SUCCESSOR_DANGLING_REFERENCE"
REFUSED_NONRECIPROCAL = "REFUSED_CAREER_SUCCESSOR_NONRECIPROCAL_LINEAGE"
REFUSED_INCOMPATIBLE = "REFUSED_CAREER_SUCCESSOR_DISPOSITION_INCOMPATIBLE"
REFUSED_A04_MAPPING = "REFUSED_CAREER_SUCCESSOR_A04_MAPPING_BROKEN"
REFUSED_RAW_EVIDENCE_ABSENT = "REFUSED_CAREER_SUCCESSOR_RAW_EVIDENCE_ABSENT"
REFUSED_RAW_FILE_ABSENT = "REFUSED_CAREER_SUCCESSOR_RAW_FILE_ABSENT"
REFUSED_RAW_TEXT = "REFUSED_CAREER_SUCCESSOR_RAW_REVISION_TEXT_CHANGED"
REFUSED_RAW_SPAN = "REFUSED_CAREER_SUCCESSOR_RAW_SPAN_MISMATCH"
# v37.6 (MF37A05-01): every lineage edge and every raw capture is a typed semantic binding.
REFUSED_PREDECESSOR_IDENTITY = "REFUSED_CAREER_SUCCESSOR_PREDECESSOR_IDENTITY_MISMATCH"
REFUSED_SOURCE_LOCATOR = "REFUSED_CAREER_SUCCESSOR_SOURCE_LOCATOR_MISMATCH"
REFUSED_A04_IDENTITY = "REFUSED_CAREER_SUCCESSOR_A04_IDENTITY_MISMATCH"
REFUSED_RAW_PAGE = "REFUSED_CAREER_SUCCESSOR_RAW_PAGE_OR_REVISION_MISMATCH"
REFUSED_PAGE_IDENTITY = "REFUSED_CAREER_SUCCESSOR_PAGE_IDENTITY_MISMATCH"
VERIFIER_VERSION = "BAS-C37A06-CAREER-SUCCESSOR-VERIFIER-v2"
#: What every row of one revision page states identically: the capture, its text, its title, the display name the
#: page is served under and its Wikidata item. A person is identified by the page, never by the display name.
PAGE_IDENTITY_NAMES = ("page_title", "person_display", "wikidata_qid")
PAGE_IDENTITY_FIELDS = ("revision", "raw_file_sha256", "wikitext_sha256") + PAGE_IDENTITY_NAMES

_HEX64 = re.compile(r"[0-9a-f]{64}")
_FAMILIES = ("COACHING", "PLAYING", "ADMINISTRATIVE")
#: Any versioned episode identity: ``<prefix>:<pageid>:<revision>:<family>:<row>:<interval>``.
_IDENTITY = re.compile(rf"^([A-Za-z0-9-]+):(\d+):(\d+):({'|'.join(_FAMILIES)}):(\d+):(\d+)$")


def parse_identity(identity: Any) -> tuple[str, str, str, str, str, str] | None:
    """(prefix, pageid, revision, family, row, interval) of a versioned identity, or None when it is not one."""

    match = _IDENTITY.match(str(identity))
    return tuple(match.group(i) for i in range(1, 7)) if match else None  # type: ignore[return-value]


def _locator_of(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return str(row.get("pageid")), str(row.get("revision")), str(row.get("family"))


def _page_identity(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(row.get(field)) for field in PAGE_IDENTITY_FIELDS)


def display_name_of_title(title: Any) -> str:
    """The display name a page is served under: its title without the trailing disambiguation parenthetical."""

    return re.sub(r"\s*\(.*\)$", "", str(title or ""))


@dataclass(frozen=True)
class Format:
    version: str
    episode_table: str
    disposition_table: str
    episode_columns: tuple[str, ...]
    identity_prefix: str
    a04_table: str | None = None


FORMATS = {
    FORMAT_VERSION: Format(FORMAT_VERSION, EPISODE_TABLE, DISPOSITION_TABLE, EPISODE_COLUMNS, IDENTITY_PREFIX),
    A05_FORMAT_VERSION: Format(A05_FORMAT_VERSION, A05_EPISODE_TABLE, A05_DISPOSITION_TABLE, A05_EPISODE_COLUMNS,
                               A05_IDENTITY_PREFIX, A05_FROM_A04_TABLE),
}
_VERSION_OF_FORMAT = {FORMAT_VERSION: SUCCESSOR_VERSION, A05_FORMAT_VERSION: A05_SUCCESSOR_VERSION}


class CareerSuccessorError(ValueError):
    """A refusal to serve a career successor. ``code`` is stable; the message names the cause."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_row(values: Iterable[Any]) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"), default=str)


def row_digest(values: Iterable[Any]) -> str:
    return hashlib.sha256(canonical_row(values).encode("utf-8")).hexdigest()


def predecessor_row_digest(row: Mapping[str, Any]) -> str:
    """The content digest of one delivered predecessor row, over its columns in the delivered order."""

    return row_digest(row.get(column) for column in PREDECESSOR_COLUMNS)


def episode_row_digest(row: Mapping[str, Any], columns: tuple[str, ...] = EPISODE_COLUMNS) -> str:
    """The content digest of one successor episode row (an Attempt 4 row, for the Attempt 5 mapping)."""

    return row_digest(row.get(column) for column in columns)


def table_ledger(conn: sqlite3.Connection, table: str, columns: tuple[str, ...], key: str) -> tuple[str, int]:
    """(SHA-256 over every row in key order, row count): the digest a successor declares for a table."""

    digest = hashlib.sha256()
    count = 0
    column_list = ", ".join(f'"{column}"' for column in columns)
    for row in conn.execute(f'SELECT {column_list} FROM {table} ORDER BY "{key}"'):
        digest.update(canonical_row(tuple(row)).encode("utf-8"))
        digest.update(b"\n")
        count += 1
    return digest.hexdigest(), count


def identity(conn: sqlite3.Connection, schema: str = "main") -> dict[str, str]:
    return {str(row[0]): str(row[1]) for row in conn.execute(f"SELECT key, value FROM {schema}.{IDENTITY_TABLE}")}


def _tables(conn: sqlite3.Connection, schema: str) -> set[str]:
    return {str(row[0]) for row in conn.execute(f"SELECT name FROM {schema}.sqlite_master WHERE type='table'")}


def _id_list(value: Any, what: str, owner: str) -> list[str]:
    try:
        decoded = json.loads(value) if isinstance(value, str) else value
    except ValueError as error:
        raise CareerSuccessorError(REFUSED_MALFORMED_LINEAGE, f"{what} of {owner} is not JSON: {error}") from error
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise CareerSuccessorError(REFUSED_MALFORMED_LINEAGE, f"{what} of {owner} is not a list of identities")
    if len(decoded) != len(set(decoded)):
        raise CareerSuccessorError(REFUSED_MALFORMED_LINEAGE, f"{what} of {owner} repeats an identity")
    return decoded


def _examples(values: Iterable[Any], limit: int = 5) -> list[Any]:
    return sorted(values, key=str)[:limit]


def _check_lineage(conn: sqlite3.Connection, fmt: Format, declared: dict[str, str]) -> dict[str, Any]:
    """Structural and semantic lineage, proven from the rows themselves (MF37A04-02). Returns the counts it proved."""

    schema = ATTACHED_SCHEMA
    predecessors = {str(row[0]) for row in conn.execute(f"SELECT episode_id FROM main.{PREDECESSOR_TABLE}")}
    a05 = fmt.a04_table is not None
    extra = ", a04_episode_ids, a04_lineage_state, a04_disposition" if a05 else ""
    episodes = [dict(zip(("episode_id", "pageid", "revision", "family", "row_index", "interval_index",
                          "predecessor_episode_ids", "lineage_state", "disposition", "raw_file", "raw_file_sha256",
                          "wikitext_sha256", *PAGE_IDENTITY_NAMES,
                          *(("a04_episode_ids", "a04_lineage_state", "a04_disposition") if a05 else ())),
                         row))
                for row in conn.execute(
                    "SELECT episode_id, pageid, revision, family, row_index, interval_index, predecessor_episode_ids, "
                    f"lineage_state, disposition, raw_file, raw_file_sha256, wikitext_sha256, "
                    f"{', '.join(PAGE_IDENTITY_NAMES)}{extra} FROM {schema}.{fmt.episode_table}")]
    dispositions = [dict(zip(("predecessor_episode_id", "disposition", "successor_episode_ids",
                              "predecessor_row_sha256"), row)) for row in
                    conn.execute(f"SELECT predecessor_episode_id, disposition, successor_episode_ids, "
                                 f"predecessor_row_sha256 FROM {schema}.{fmt.disposition_table}")]
    identities = [str(row["episode_id"]) for row in episodes]
    identity_set = set(identities)
    # Identities: unique, versioned, and equal to the row's own locator.
    pattern = re.compile(rf"^{fmt.identity_prefix}:(\d+):(\d+):({'|'.join(_FAMILIES)}):(\d+):(\d+)$")
    wrong = []
    for row in episodes:
        match = pattern.match(str(row["episode_id"]))
        if match is None or [match.group(i) for i in range(1, 6)] != [
                str(row["pageid"]), str(row["revision"]), str(row["family"]), str(row["row_index"]),
                str(row["interval_index"])]:
            wrong.append(row["episode_id"])
    if wrong:
        raise CareerSuccessorError(REFUSED_INVALID_IDENTITY, (
            f"{len(wrong)} episode identit(ies) are outside {fmt.identity_prefix}:<page>:<revision>:<family>:<row>:"
            f"<interval> or disagree with their row's own locator: {_examples(wrong)}"))
    # Edges, both ways.
    forward: set[tuple[str, str]] = set()
    produced_by: dict[str, set[str]] = {}
    dangling = set()
    incompatible = []
    for row in dispositions:
        owner = str(row["predecessor_episode_id"])
        successors = _id_list(row["successor_episode_ids"], "successor_episode_ids", owner)
        if row["disposition"] not in DISPOSITIONS:
            incompatible.append(f"{owner}: unknown disposition {row['disposition']!r}")
        elif (row["disposition"] == NOT_PRODUCED) != (not successors):
            incompatible.append(f"{owner}: {row['disposition']} with {len(successors)} successor row(s)")
        for successor in successors:
            if successor not in identity_set:
                dangling.add(f"{owner} -> {successor}")
            forward.add((owner, successor))
            produced_by.setdefault(successor, set()).add(str(row["disposition"]))
    backward: set[tuple[str, str]] = set()
    added_state = ADDED_STATES[fmt.version]
    for row in episodes:
        owner = str(row["episode_id"])
        parents = _id_list(row["predecessor_episode_ids"], "predecessor_episode_ids", owner)
        row["_parents"] = parents
        for parent in parents:
            if parent not in predecessors:
                dangling.add(f"{owner} <- {parent}")
            backward.add((parent, owner))
        expected_state = DERIVED if parents else added_state
        if row["lineage_state"] != expected_state:
            incompatible.append(f"{owner}: lineage_state {row['lineage_state']!r} with {len(parents)} predecessor(s)")
        expected_disposition = ",".join(sorted(produced_by.get(owner, ()))) or "ADDED"
        if row["disposition"] != expected_disposition:
            incompatible.append(f"{owner}: disposition {row['disposition']!r}, but the dispositions naming it say "
                                f"{expected_disposition!r}")
    if dangling:
        raise CareerSuccessorError(REFUSED_DANGLING, (
            f"{len(dangling)} lineage reference(s) name a row that does not exist: {_examples(dangling)}"))
    if forward != backward:
        raise CareerSuccessorError(REFUSED_NONRECIPROCAL, (
            f"the dispositions state {len(forward - backward)} edge(s) the episodes do not, and the episodes "
            f"{len(backward - forward)} the dispositions do not: {_examples(forward ^ backward)}"))
    if incompatible:
        raise CareerSuccessorError(REFUSED_INCOMPATIBLE, (
            f"{len(incompatible)} disposition/lineage state(s) contradict their edges: {_examples(incompatible)}"))
    # Raw provenance present for every row (it is verified against the bytes when a row is served); absent evidence
    # is refused as absent before any binding compares it.
    absent = [row["episode_id"] for row in episodes
              if not row["raw_file"] or not _HEX64.fullmatch(str(row["raw_file_sha256"] or ""))
              or not _HEX64.fullmatch(str(row["wikitext_sha256"] or ""))]
    if absent:
        raise CareerSuccessorError(REFUSED_RAW_EVIDENCE_ABSENT, (
            f"{len(absent)} row(s) name no raw revision file, or no well-formed SHA-256 of it or of its revision "
            f"text: {_examples(absent)}"))
    bound = _check_predecessor_bindings(conn, episodes, dispositions)
    proved: dict[str, Any] = {"episodes": len(identities), "dispositions": len(dispositions),
                              "predecessor_rows": len(predecessors), "edges": len(forward),
                              "episodes_added_without_predecessor": sum(1 for r in episodes
                                                                        if r["lineage_state"] == added_state),
                              "predecessor_rows_not_produced": sum(1 for r in dispositions
                                                                   if r["disposition"] == NOT_PRODUCED),
                              "rows_with_raw_provenance": len(episodes), **bound,
                              "verifier_version": VERIFIER_VERSION}
    if a05:
        proved.update(_check_a04_mapping(conn, episodes, identity_set, declared))
    return proved


def _check_predecessor_bindings(conn: sqlite3.Connection, episodes: list[dict[str, Any]],
                                dispositions: list[dict[str, Any]]) -> dict[str, Any]:
    """v37.6 (MF37A05-01): every parent edge is a typed binding to the predecessor's own page, revision, family and
    raw locator, and every disposition's predecessor digest is recomputed from the open predecessor's actual row."""

    columns = ", ".join(f'"{column}"' for column in PREDECESSOR_COLUMNS)
    locators: dict[str, tuple[Any, ...]] = {}
    digests: dict[str, str] = {}
    predecessor_pages: dict[str, set[tuple[str, ...]]] = {}
    for values in conn.execute(f"SELECT {columns} FROM main.{PREDECESSOR_TABLE}"):
        row = dict(zip(PREDECESSOR_COLUMNS, values))
        identity = str(row["episode_id"])
        locators[identity] = (_locator_of(row), str(row.get("raw_file_sha256")), str(row.get("wikitext_sha256")))
        digests[identity] = row_digest(values)
        predecessor_pages.setdefault(str(row.get("pageid")), set()).add(_page_identity(row))
    identity_mismatch, locator_mismatch = [], []
    for row in episodes:
        owner = str(row["episode_id"])
        own = _locator_of(row)
        for parent in row.get("_parents") or ():
            parsed = parse_identity(parent)
            locator, raw_sha256, text_sha256 = locators[parent]
            if parsed is None or tuple(parsed[1:4]) != own or locator != own:
                identity_mismatch.append(f"{owner} <- {parent}")
            elif raw_sha256 != str(row["raw_file_sha256"]) or text_sha256 != str(row["wikitext_sha256"]):
                locator_mismatch.append(f"{owner} <- {parent}")
    if identity_mismatch:
        raise CareerSuccessorError(REFUSED_PREDECESSOR_IDENTITY, (
            f"{len(identity_mismatch)} edge(s) name a predecessor row of another page, revision or family than the "
            f"row that claims it (a display name is not an identity): {_examples(identity_mismatch)}"))
    if locator_mismatch:
        raise CareerSuccessorError(REFUSED_SOURCE_LOCATOR, (
            f"{len(locator_mismatch)} row(s) carry raw evidence (capture or revision-text digest) that is not their "
            f"predecessor row's own: {_examples(locator_mismatch)}"))
    # A page is one person's revision: every row of it states the same capture, text, title, display name and
    # Wikidata item, and a page the predecessor also carries states exactly the predecessor's (MF37A05-01; this also
    # binds rows added without a predecessor row, through their page).
    successor_pages: dict[str, set[tuple[str, ...]]] = {}
    for row in episodes:
        successor_pages.setdefault(str(row["pageid"]), set()).add(_page_identity(row))
    split = sorted(page for page, states in successor_pages.items() if len(states) > 1)
    if split:
        raise CareerSuccessorError(REFUSED_PAGE_IDENTITY, (
            f"{len(split)} page(s) whose rows disagree on the page's revision, capture, title, display name or "
            f"Wikidata item: {_examples(split)}"))
    moved = sorted(page for page, states in successor_pages.items()
                   if page in predecessor_pages and not states <= predecessor_pages[page])
    if moved:
        raise CareerSuccessorError(REFUSED_PAGE_IDENTITY, (
            f"{len(moved)} page(s) state an identity the predecessor's rows of the same page do not: "
            f"{_examples(moved)}"))
    changed = [str(row["predecessor_episode_id"]) for row in dispositions
               if digests.get(str(row["predecessor_episode_id"])) != str(row.get("predecessor_row_sha256"))]
    if changed:
        raise CareerSuccessorError(REFUSED_ROW_BINDING, (
            f"{len(changed)} disposition(s) record a predecessor-row digest the open predecessor's row does not "
            f"hash to: {_examples(changed)}"))
    edges = sum(len(r.get("_parents") or ()) for r in episodes)
    return {"parent_edges_bound_to_page_revision_family": edges, "parent_edges_bound_to_raw_locator": edges,
            "dispositions_bound_to_predecessor_row_digest": len(dispositions),
            "pages_uniform": len(successor_pages),
            "pages_bound_to_predecessor_page_identity": sum(1 for page in successor_pages if page in predecessor_pages),
            "pages_without_predecessor_rows": sum(1 for page in successor_pages if page not in predecessor_pages)}


def _check_a04_mapping(conn: sqlite3.Connection, episodes: list[dict[str, Any]], identity_set: set[str],
                       declared: dict[str, str]) -> dict[str, Any]:
    rows = [dict(zip(("a04_episode_id", "disposition", "a05_episode_ids", "a04_row_sha256"), row)) for row in
            conn.execute(f"SELECT a04_episode_id, disposition, a05_episode_ids, a04_row_sha256 "
                         f"FROM {ATTACHED_SCHEMA}.{A05_FROM_A04_TABLE}")]
    ids = [str(row["a04_episode_id"]) for row in rows]
    problems = []
    if len(ids) != len(set(ids)):
        problems.append(f"{len(ids) - len(set(ids))} repeated Attempt 4 identit(ies)")
    if str(len(set(ids))) != declared.get("a04_successor_row_count"):
        problems.append(f"{len(set(ids))} Attempt 4 rows mapped; the successor declares "
                        f"{declared.get('a04_successor_row_count')}")
    bad_ids = [i for i in ids if not re.match(rf"^{IDENTITY_PREFIX}:\d+:\d+:(?:{'|'.join(_FAMILIES)}):\d+:\d+$", i)]
    if bad_ids:
        problems.append(f"Attempt 4 identities outside {IDENTITY_PREFIX}: {_examples(bad_ids)}")
    forward, produced_by, dangling = set(), {}, set()
    for row in rows:
        owner = str(row["a04_episode_id"])
        targets = _id_list(row["a05_episode_ids"], "a05_episode_ids", owner)
        if row["disposition"] not in DISPOSITIONS or (row["disposition"] == NOT_PRODUCED) != (not targets):
            problems.append(f"{owner}: {row['disposition']} with {len(targets)} Attempt 5 row(s)")
        for target in targets:
            if target not in identity_set:
                dangling.add(f"{owner} -> {target}")
            forward.add((owner, target))
            produced_by.setdefault(target, set()).add(str(row["disposition"]))
    backward = set()
    id_set = set(ids)
    typed_mismatch = []
    for row in episodes:
        owner = str(row["episode_id"])
        parents = _id_list(row["a04_episode_ids"], "a04_episode_ids", owner)
        row["_a04_parents"] = parents
        for parent in parents:
            if parent not in id_set:
                dangling.add(f"{owner} <- {parent}")
            backward.add((parent, owner))
            parsed = parse_identity(parent)
            if parsed is None or tuple(parsed[1:4]) != _locator_of(row):
                typed_mismatch.append(f"{owner} <- {parent}")
        if row["a04_lineage_state"] != (A04_DERIVED if parents else A04_ADDED):
            problems.append(f"{owner}: a04_lineage_state {row['a04_lineage_state']!r} with {len(parents)} parent(s)")
        if row["a04_disposition"] != (",".join(sorted(produced_by.get(owner, ()))) or "ADDED_IN_A05"):
            problems.append(f"{owner}: a04_disposition {row['a04_disposition']!r} disagrees with the mapping")
    if dangling:
        problems.append(f"{len(dangling)} dangling Attempt 4 reference(s): {_examples(dangling)}")
    if forward != backward:
        problems.append(f"{len(forward ^ backward)} nonreciprocal Attempt 4 edge(s): {_examples(forward ^ backward)}")
    if typed_mismatch:
        raise CareerSuccessorError(REFUSED_A04_IDENTITY, (
            f"{len(typed_mismatch)} Attempt 4 edge(s) name a row of another page, revision or family than the row "
            f"that claims it: {_examples(typed_mismatch)}"))
    file_check = "A04_FILE_NOT_DECLARED"
    locators_bound = 0
    path = declared.get("a04_successor_path")
    if path:
        a04 = Path(path)
        if not a04.is_file():
            file_check = "A04_FILE_ABSENT_SET_EQUALITY_NOT_CHECKED"
        elif sha256_file(a04) != declared.get("a04_successor_sha256"):
            problems.append(f"the declared Attempt 4 file {a04} no longer has its declared SHA-256")
        else:
            other = sqlite3.connect(f"file:{a04.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
            columns = ", ".join(f'"{column}"' for column in EPISODE_COLUMNS)
            a04_locators: dict[str, tuple[str, str]] = {}
            a04_digests: dict[str, str] = {}
            try:
                for values in other.execute(f"SELECT {columns} FROM {EPISODE_TABLE}"):
                    a04_row = dict(zip(EPISODE_COLUMNS, values))
                    a04_locators[str(a04_row["episode_id"])] = (str(a04_row.get("raw_file_sha256")),
                                                                str(a04_row.get("wikitext_sha256")))
                    a04_digests[str(a04_row["episode_id"])] = row_digest(values)
            finally:
                other.close()
            actual = set(a04_locators)
            if actual != id_set:
                problems.append(f"the Attempt 4 mapping is not the Attempt 4 file's identity set: "
                                f"{len(actual - id_set)} missing, {len(id_set - actual)} extra")
            # v37.6: the mapping binds to the Attempt 4 file's actual rows -- their raw locator equals the Attempt 5
            # row's, and each mapping row's recorded digest is what the file's row hashes to.
            locator_mismatch = [f"{row['episode_id']} <- {parent}" for row in episodes
                                for parent in row.get("_a04_parents") or ()
                                if parent in a04_locators and a04_locators[parent] != (str(row["raw_file_sha256"]),
                                                                                       str(row["wikitext_sha256"]))]
            if locator_mismatch:
                raise CareerSuccessorError(REFUSED_A04_IDENTITY, (
                    f"{len(locator_mismatch)} row(s) carry raw evidence that is not their Attempt 4 row's own: "
                    f"{_examples(locator_mismatch)}"))
            digest_mismatch = [str(row["a04_episode_id"]) for row in rows
                               if a04_digests.get(str(row["a04_episode_id"])) != str(row.get("a04_row_sha256"))]
            if digest_mismatch:
                problems.append(f"{len(digest_mismatch)} mapping row(s) record a digest the Attempt 4 file's row does "
                                f"not hash to: {_examples(digest_mismatch)}")
            locators_bound = sum(len(row.get("_a04_parents") or ()) for row in episodes)
            file_check = "A04_FILE_IDENTITY_SET_EQUAL"
    if problems:
        raise CareerSuccessorError(REFUSED_A04_MAPPING, f"the Attempt 4 mapping is broken: {problems[:5]}")
    return {"a04_rows_mapped": len(ids), "a04_edges": len(forward), "a04_file_check": file_check,
            "a04_edges_bound_to_page_revision_family": len(backward),
            "a04_edges_bound_to_a04_file_raw_locator": locators_bound,
            "a04_mapping_digests_bound_to_a04_file_rows": file_check == "A04_FILE_IDENTITY_SET_EQUAL",
            "a04_rows_not_produced": sum(1 for r in rows if r["disposition"] == NOT_PRODUCED),
            "episodes_added_without_a04_row": sum(1 for r in episodes if r["a04_lineage_state"] == A04_ADDED)}


def attach_successor(conn: sqlite3.Connection, successor: Path | str, *, database: Path | str,
                     expected_sha256: str | None = None) -> dict[str, Any]:
    """Validate a successor against the open predecessor and expose it as :data:`VIEW_NAME`.

    ``conn`` is the read-only connection to the predecessor at ``database``. Every refusal happens before any
    successor row is read by a query. Returns the binding every served answer repeats.
    """

    path = Path(successor)
    if not path.is_file():
        raise CareerSuccessorError(REFUSED_ABSENT, f"no career successor file at {path}")
    file_sha256 = sha256_file(path)
    if expected_sha256 is not None and file_sha256 != expected_sha256.lower():
        raise CareerSuccessorError(REFUSED_FILE_DIGEST,
                                   f"the successor file hashes to {file_sha256}, not the pinned {expected_sha256}")
    # A literal read-only URI, not a bound parameter: a canonical write guard can verify a literal ATTACH
    # target as read-only, and it refuses one it cannot see.
    uri = (path.resolve().as_uri() + "?mode=ro&immutable=1").replace("'", "''")
    conn.execute(f"ATTACH DATABASE '{uri}' AS {ATTACHED_SCHEMA}")
    try:
        present = _tables(conn, ATTACHED_SCHEMA)
        if IDENTITY_TABLE not in present:
            raise CareerSuccessorError(REFUSED_NOT_A_SUCCESSOR, f"the successor lacks table {IDENTITY_TABLE}")
        declared = identity(conn, ATTACHED_SCHEMA)
        fmt = FORMATS.get(declared.get("format_version", ""))
        if fmt is None or declared.get("successor_version") != _VERSION_OF_FORMAT[fmt.version]:
            raise CareerSuccessorError(REFUSED_VERSION, (
                f"format {declared.get('format_version')!r} / successor {declared.get('successor_version')!r} is not "
                f"one of {sorted((f, v) for f, v in _VERSION_OF_FORMAT.items())}"))
        tables = (fmt.episode_table, fmt.disposition_table) + ((fmt.a04_table,) if fmt.a04_table else ())
        missing = [name for name in tables if name not in present]
        if missing:
            raise CareerSuccessorError(REFUSED_NOT_A_SUCCESSOR, f"the successor lacks table(s) {missing}")
        predecessor_sha256 = sha256_file(database)
        if declared.get("predecessor_database_sha256") != predecessor_sha256:
            raise CareerSuccessorError(REFUSED_PREDECESSOR, (
                f"the successor corrects predecessor {declared.get('predecessor_database_sha256')}, but the open "
                f"database is {predecessor_sha256}"))
        if declared.get("default_activation") != NOT_ACTIVATED:
            raise CareerSuccessorError(REFUSED_ACTIVATION, (
                f"the successor states default_activation={declared.get('default_activation')!r}; activation is a "
                "separate owner decision this consumer never infers from a file"))
        if declared.get("acceptance_state") != NOT_ACCEPTED or declared.get("pit_admitted") != "0" or \
                declared.get("evidence_class") != EVIDENCE_CLASS:
            raise CareerSuccessorError(REFUSED_AUTHORITY, (
                "the successor claims acceptance, point-in-time admission or an evidence class beyond retrospective "
                f"secondary revisions: acceptance_state={declared.get('acceptance_state')!r}, "
                f"pit_admitted={declared.get('pit_admitted')!r}, evidence_class={declared.get('evidence_class')!r}"))
        ledgers = [(fmt.episode_table, fmt.episode_columns, "episode_id"),
                   (fmt.disposition_table, DISPOSITION_COLUMNS, "predecessor_episode_id")]
        if fmt.a04_table:
            ledgers.append((fmt.a04_table, A04_MAP_COLUMNS, "a04_episode_id"))
        for table, columns, key in ledgers:
            digest, count = table_ledger(conn, f"{ATTACHED_SCHEMA}.{table}", columns, key)
            if declared.get(f"ledger::{table}::sha256") != digest or declared.get(f"ledger::{table}::rows") != str(count):
                raise CareerSuccessorError(REFUSED_LEDGER, (
                    f"{table} re-hashes to {digest} over {count} rows; the successor declares "
                    f"{declared.get(f'ledger::{table}::sha256')} over {declared.get(f'ledger::{table}::rows')}"))
        bad_rows = conn.execute(
            f"SELECT COUNT(*) FROM {ATTACHED_SCHEMA}.{fmt.episode_table} WHERE CAST(pit_admitted AS INTEGER) != 0 "
            "OR evidence_class IS NOT ? ", (EVIDENCE_CLASS,)).fetchone()[0]
        if bad_rows:
            raise CareerSuccessorError(REFUSED_AUTHORITY, f"{bad_rows} successor row(s) claim point-in-time admission "
                                                          "or another evidence class")
        checks = {
            "predecessor_rows_without_a_disposition": (
                f"SELECT COUNT(*) FROM main.{PREDECESSOR_TABLE} p LEFT JOIN {ATTACHED_SCHEMA}.{fmt.disposition_table} d "
                "ON d.predecessor_episode_id = p.episode_id WHERE d.predecessor_episode_id IS NULL"),
            "dispositions_without_a_predecessor_row": (
                f"SELECT COUNT(*) FROM {ATTACHED_SCHEMA}.{fmt.disposition_table} d LEFT JOIN main.{PREDECESSOR_TABLE} p "
                "ON p.episode_id = d.predecessor_episode_id WHERE p.episode_id IS NULL"),
            "repeated_predecessor_dispositions": (
                f"SELECT COUNT(*) - COUNT(DISTINCT predecessor_episode_id) FROM {ATTACHED_SCHEMA}.{fmt.disposition_table}"),
            "repeated_successor_identities": (
                f"SELECT COUNT(*) - COUNT(DISTINCT episode_id) FROM {ATTACHED_SCHEMA}.{fmt.episode_table}"),
            "successor_identities_outside_the_versioned_namespace": (
                f"SELECT COUNT(*) FROM {ATTACHED_SCHEMA}.{fmt.episode_table} "
                f"WHERE episode_id NOT LIKE '{fmt.identity_prefix}:%'"),
            "unknown_dispositions": (
                f"SELECT COUNT(*) FROM {ATTACHED_SCHEMA}.{fmt.disposition_table} WHERE disposition NOT IN "
                f"({', '.join(repr(value) for value in sorted(DISPOSITIONS))})"),
        }
        counts = {name: int(conn.execute(sql).fetchone()[0]) for name, sql in checks.items()}
        broken = {name: value for name, value in counts.items() if value}
        if broken:
            raise CareerSuccessorError(REFUSED_COVERAGE, f"identity coverage is broken: {broken}")
        predecessor_rows = int(conn.execute(f"SELECT COUNT(*) FROM main.{PREDECESSOR_TABLE}").fetchone()[0])
        if declared.get("predecessor_row_count") != str(predecessor_rows):
            raise CareerSuccessorError(REFUSED_COVERAGE, (
                f"the successor declares {declared.get('predecessor_row_count')} predecessor rows; the open "
                f"predecessor has {predecessor_rows}"))
        lineage = _check_lineage(conn, fmt, declared)
        conn.execute(f"CREATE TEMP VIEW IF NOT EXISTS {VIEW_NAME} AS SELECT * FROM {ATTACHED_SCHEMA}.{fmt.episode_table}")
    except BaseException:
        try:
            conn.execute(f"DETACH DATABASE {ATTACHED_SCHEMA}")
        except sqlite3.Error:
            pass
        raise
    return {
        "successor_file": str(path.resolve()),
        "successor_file_sha256": file_sha256,
        "successor_version": declared["successor_version"],
        "format_version": declared["format_version"],
        "predecessor_database": str(Path(database).resolve()),
        "predecessor_database_sha256": predecessor_sha256,
        "predecessor_table": declared.get("predecessor_table"),
        "predecessor_row_count": predecessor_rows,
        "parser_version": declared.get("parser_version"),
        "predecessor_parser_version": declared.get("predecessor_parser_version"),
        "identity_rule": declared.get("identity_rule"),
        "default_activation": declared["default_activation"],
        "acceptance_state": declared["acceptance_state"],
        "ledger": {table: declared.get(f"ledger::{table}::sha256") for table, _, _ in ledgers},
        "coverage_checks": counts,
        "lineage_proved_independently_of_the_ledgers": lineage,
        "verifier_version": VERIFIER_VERSION,
        "attached_schema": ATTACHED_SCHEMA,
        "episode_table": fmt.episode_table,
        "disposition_table": fmt.disposition_table,
        "a04_table": fmt.a04_table,
        "a04_successor_sha256": declared.get("a04_successor_sha256"),
        "superseded_semantics": (None if fmt.version == A05_FORMAT_VERSION else
                                 "The Attempt 4 format reads two-endpoint season templates as their first year and "
                                 "lets a defensive passing-game coordinator carry the OFFENSE unit (MF37A04-03/04); "
                                 "the Attempt 5 successor corrects both."),
        "selection": "EXPLICIT_CAREER_SUCCESSOR",
        "note": ("Selected by name for this answer only. The predecessor database, its default answer and its "
                 "raw captures are unchanged; this successor is neither activated nor accepted."),
    }


def _payload_page(data: bytes) -> dict[str, Any] | None:
    """The single page a cached Wikimedia API payload carries, or None when the bytes are not such a payload."""

    try:
        payload = json.loads(data)
        pages = (payload.get("query") or {}).get("pages") or {}
        if len(pages) != 1:
            return None
        page = next(iter(pages.values()))
        return page if isinstance(page, dict) else None
    except (ValueError, AttributeError, TypeError):
        return None


def _revision_text(data: bytes) -> str | None:
    """The revision wikitext a cached Wikimedia API payload carries, or None when the bytes are not one."""

    page = _payload_page(data)
    try:
        return page["revisions"][0]["slots"]["main"]["*"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        return None


def _revision_locator(data: bytes) -> tuple[str, str, Any, Any] | None:
    """(page id, revision id, title, Wikidata item or None) the payload itself states, or None when it states none."""

    page = _payload_page(data)
    try:
        return (str(page["pageid"]), str(page["revisions"][0]["revid"]), page.get("title"),  # type: ignore[index]
                (page.get("pageprops") or {}).get("wikibase_item"))  # type: ignore[union-attr]
    except (KeyError, IndexError, TypeError, AttributeError):
        return None


def _span(value: Any) -> tuple[int, int] | None:
    try:
        decoded = json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return None
    if isinstance(decoded, list) and len(decoded) == 2 and all(isinstance(v, int) for v in decoded):
        return decoded[0], decoded[1]
    return None


class RawBytesVerifier:
    """Re-read each distinct raw revision file a served row names, once per consumer run, and prove the row's raw
    evidence: the file exists, its bytes have the recorded SHA-256, the capture itself names the row's own page id
    and revision id (v37.6, MF37A05-01: a genuine capture of another page is refused whatever its digests say), its
    revision text has the recorded SHA-256, and every recorded character span holds the row's recorded text. An
    absent value is refused, never passed."""

    def __init__(self) -> None:
        self.seen: dict[str, tuple[str, str | None, tuple[str, str, Any] | None] | None] = {}

    def verify(self, row: Mapping[str, Any]) -> dict[str, Any]:
        episode = row.get("episode_id")
        path = str(row.get("raw_file") or "")
        declared = str(row.get("raw_file_sha256") or "")
        if not path or not _HEX64.fullmatch(declared):
            raise CareerSuccessorError(REFUSED_RAW_EVIDENCE_ABSENT, (
                f"row {episode} names raw file {path or None!r} with SHA-256 {declared or None!r}; absent raw evidence "
                "is never labelled verified"))
        if path not in self.seen:
            source = Path(path)
            if not source.is_file():
                self.seen[path] = None
            else:
                data = source.read_bytes()
                self.seen[path] = (hashlib.sha256(data).hexdigest(), _revision_text(data), _revision_locator(data))
        entry = self.seen[path]
        if entry is None:
            raise CareerSuccessorError(REFUSED_RAW_FILE_ABSENT, f"row {episode} names raw file {path}, which is absent")
        if entry[0] != declared:
            raise CareerSuccessorError(REFUSED_RAW, (
                f"row {episode} names raw file {path} with SHA-256 {declared}, which now hashes to {entry[0]}"))
        locator = entry[2]
        own = (str(row.get("pageid")), str(row.get("revision")), row.get("page_title"))
        if locator is None or (locator[0], locator[1], locator[2]) != own:
            raise CareerSuccessorError(REFUSED_RAW_PAGE, (
                f"row {episode} states page {own[0]} revision {own[1]} titled {own[2]!r}, but its raw capture {path} "
                "is " + ("not a single-page revision capture" if locator is None else
                         f"the capture of page {locator[0]} revision {locator[1]} titled {locator[2]!r}")))
        if row.get("person_display") != display_name_of_title(locator[2]):
            raise CareerSuccessorError(REFUSED_PAGE_IDENTITY, (
                f"row {episode} is served as {row.get('person_display')!r}, but its capture's title {locator[2]!r} "
                f"names {display_name_of_title(locator[2])!r} (a display name is derived from the page, never trusted)"))
        if locator[3] is not None and locator[3] != row.get("wikidata_qid"):
            raise CareerSuccessorError(REFUSED_PAGE_IDENTITY, (
                f"row {episode} states Wikidata item {row.get('wikidata_qid')!r}; its capture states {locator[3]!r}"))
        result: dict[str, Any] = {"raw_file_sha256": True, "raw_page_revision_and_title": True,
                                  "display_name_derived_from_capture_title": True,
                                  "wikidata_item": "AGREES_WITH_CAPTURE" if locator[3] is not None
                                  else "NOT_STATED_BY_CAPTURE"}
        wikitext_digest = row.get("wikitext_sha256")
        if wikitext_digest:
            text = entry[1]
            if text is None or hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest() != wikitext_digest:
                raise CareerSuccessorError(REFUSED_RAW_TEXT, (
                    f"row {episode}: the revision text in {path} no longer hashes to {wikitext_digest}"))
            result["wikitext_sha256"] = True
            for field, value_field in (("team_char_span", "team_raw"), ("years_char_span", "years_raw")):
                span = _span(row.get(field))
                if span is None:
                    result[field] = "NOT_RECORDED"
                    continue
                if text[span[0]:span[1]] != row.get(value_field):
                    raise CareerSuccessorError(REFUSED_RAW_SPAN, (
                        f"row {episode}: {field} {list(span)} holds {text[span[0]:span[1]][:80]!r}, not the row's "
                        f"{value_field} {str(row.get(value_field))[:80]!r}"))
                result[field] = True
        else:
            result["wikitext_sha256"] = "NOT_RECORDED"
        return result


def verify_raw_bytes(rows: Iterable[Mapping[str, Any]], verifier: RawBytesVerifier | None = None) -> int:
    verifier = verifier or RawBytesVerifier()
    count = 0
    for row in rows:
        verifier.verify(row)
        count += 1
    return count
