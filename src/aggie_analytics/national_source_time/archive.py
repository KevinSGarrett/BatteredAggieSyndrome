r"""Explicit archived-publication evidence for the source-time query (BAT-713, Cycle #41 TP41-A01; contract V1.2).

``bas-source-time-query --database <source-time sqlite> --archive-evidence
<canonical\national_archived_publication_2019\sha256\<id>\national_archived_publication.sqlite> --grain contest
--contest ncaa:1735109 --cutoff 2019-09-02T01:00:50.999999Z``

Standard library only (plus the shared field-grain module), imported only when ``--archive-evidence`` is given;
without it the source-time consumer is unchanged. Opening a sidecar verifies its location, run manifest identity
document, SQLite bytes, schema, labels, counts and natural keys, and that its parent is exactly the opened source-time
database. It then trusts no stored label or stored record:

* The sidecar must name an issued authority: the committed contract (sha256), its retained acquisition document, its
  parent source-time binding and its route control. The exact issued tranche bytes are packaged with this module
  (``national_archived_publication_2019_tranche.json``, sha256 bound by contract scope.tranche_sha256), so the
  tranche keys, classification pairs, strata, selection roles and candidate locators come from the issued tranche, not
  from the sidecar (MF41A01-06, second same-attempt continuation).
* Every raw payload is rehashed; the acquisition document and the control receipts are rehashed.
* Every request record must equal the acquisition receipt plus its re-derived raw-store path and availability answer
  (re-read from the retained body); requests, dispositions, captures and assertions must be in the payload order.
* The complete expected capture collection -- the retained control plus every receipted replayed version, quarantined
  versions included -- is enumerated from the receipts and compared, by identity and multiplicity, with the stored
  captures before any per-capture check: a missing, extra, duplicated or reordered version refuses.
* Every stored witness (witness, byte span, literal) must be exactly one of the occurrences this module's own
  field-grain extraction finds in the raw page (attributes tokenized from the start tag, complete text of closed
  text-only elements, line-start JS assignments); every capture and assertion record -- scopes, page facts, the
  evidenced participant mapping (documented parent names, CFBD route role and date; numeric ESPN/CFBD ids are never
  equated), field states, clocks and the complete witness rows -- is re-derived from the raw bytes, receipts and the
  parent's lineage and must equal the stored record. Qualified participant mappings must agree across the tranche, and
  a version whose participants do not map is quarantined whole.
* Every disposition record must equal the one reconstructed from the issued tranche row, the parent contest record,
  the acquisition receipts and the key's complete expected capture collection.

A predecessor V1.0 or V1.1 sidecar is checked for exact witness occurrences and then refused as superseded (V1.0
carries no evidenced participant mapping; V1.1 did not quarantine an unmapped version).

An archived version is only an upper bound for its exact witnessed field values: before the bound publication stays
UNKNOWN (outcome fields FALSE before the contest date's earliest instant), nothing is ever PIT admitted, and the
original source-time assertions, clocks and decisions are returned unchanged next to the archive evidence.
"""
from __future__ import annotations

import collections
import contextlib
import datetime as _dt
import hashlib
import json
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Any, Iterator

from aggie_analytics.national_source_time import archive_fields as af
from aggie_analytics.national_source_time import query as base

ARCHIVE_DB_FILE = "national_archived_publication.sqlite"
ARCHIVE_DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-2"
ARCHIVE_DOCUMENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-2"
LEGACY_DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-1"
LEGACY_DOCUMENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-1"
ACQUISITION_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-ACQUISITION-1"
KNOWN_CONTRACT_IDS = ("BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.2",)
LEGACY_CONTRACT_IDS = ("BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.0",)
#: Same schema as the current contract, superseded semantics (an unmapped version was not quarantined).
SUPERSEDED_CONTRACT_IDS = ("BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.1",)
#: The issued authority of contract V1.2: configs/national_archived_publication_2019_contract_v1_2.json (sha256),
#: its scope.tranche_sha256, its parent_binding.source_time and route_control, and the retained acquisition it reuses
#: (contract predecessor outputs; artifacts/data_lake/national_archived_publication_2019_v1_2_gate.json). The exact
#: issued tranche bytes are the packaged ISSUED_TRANCHE_FILE.
ISSUED_TRANCHE_FILE = "national_archived_publication_2019_tranche.json"
ISSUED_V1_2 = {
    "contract_id": "BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.2",
    "contract_sha256": "3be9f08f32d4d40dd805a31b3f402ca171add3afeeeab45256710ed1bbf8fe66",
    "tranche_sha256": "42b96f4238ccb46a2d516332e81ab35efffe22e1fdc717e340749256992e4e79",
    "acquisition_identity": "c2c0d41c269175cc35f2633ab303868bacd383764a34f2c8c70b17e17b69ccb0",
    "parent": {"source_time": {
        "content_identity": "4e1fe127a0799f5a5b6410fe6cdaaf0a876063e3e76fd2aec1fdb2188d85fa85",
        "contract_sha256": "21ed32b8fac0f5fa2c3f4dd55f29abef80437d339c3db2f1bf75206a1fcaf1bd",
        "database_identity": "9594e2bf8bba9c697a9bf0f923db77c56a9e680a9fba7daf2085dc1ec7a273ef",
        "sqlite_sha256": "5259ee091712cf46ce530e815e357ff79d7316097d7d82fe2a938afc4b9d6cb7"}},
    "control": {"contest_key": "ncaa:1735109",
                "payload_sha256": "5c32e0df631e48aadbee2af25566ce803ebd340a7619355afca5d1690ddaab19",
                "raw_receipt_sha256": "dea6a227afe16c26eaaf287270f6ec70626728f41b10fc59ef7fd75de3192692",
                "route_qualification_sha256": "75ea9fed326048c850a90fd114bfcfaf646bfd95b1f5035340d8b5ec1c31d14a"}}
ARCHIVE_GRAINS = base.ARCHIVE_GRAINS
ARCHIVE_ROW_LABELS = {"evidence_authority": "ARCHIVED_PUBLICATION_EVIDENCE_ONLY",
                      "pit_admission": "NOT_ADMITTED_NO_SEPARATE_PIT_ADMISSION_AUTHORITY",
                      "publication_inference": "ARCHIVE_CAPTURE_UPPER_BOUND_FOR_EXACT_WITNESSED_VERSION_ONLY_NOT_"
                                               "FIRST_PUBLICATION",
                      "scope": "BOUNDED_2019_TRANCHE_28_CONTESTS_NOT_NATIONAL_COVERAGE"}
#: BAT-715 expansion successor (Cycle #43 TP43-A01): the 97-key union of the issued tranche and the issued missing-prior
#: cohort, from the retained V1.2 acquisition plus the expansion acquisition. It is served only when a sidecar names it
#: explicitly; the packaged V1.2 authority above is unchanged.
EXPANSION_DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-3"
EXPANSION_DOCUMENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-3"
EXPANSION_CONTRACT_IDS = ("BAT-715-NATIONAL-ARCHIVED-PUBLICATION-2019-EXPANSION-V1.0",)
EXPANSION_ROW_LABELS = {**ARCHIVE_ROW_LABELS, "scope": "BOUNDED_2019_UNION_97_CONTESTS_RETAINED_TRANCHE_28_PLUS_"
                                                       "MISSING_PRIOR_COHORT_70_NOT_NATIONAL_COVERAGE"}
RETAINED_ORIGIN = "RETAINED_V1_2_ACQUISITION_ZERO_NEW_REQUESTS"
EXPANSION_ORIGIN = "EXPANSION_ACQUISITION_COHORT_70"
#: The exact issued cohort bytes (ARCHIVE_COHORT.json, preparation-20261005), packaged next to the tranche.
ISSUED_COHORT_FILE = "national_archived_publication_2019_expansion_cohort.json"
#: The issued expansion authority (contract, cohort, both acquisitions); None until its acquisition is finalized and
#: committed, in which case the packaged consumer serves the V1.2 sidecar only.
ISSUED_EXPANSION: dict[str, Any] | None = None
TABLES = ("meta", "dispositions", "requests", "captures", "assertions")
PAYLOADS = {"dispositions.jsonl": "dispositions", "requests.jsonl": "requests", "captures.jsonl": "captures",
            "assertions.jsonl": "assertions"}
FIELDS = base.FIELDS
WITNESSABLE = af.WITNESSABLE
QUALIFIED = af.QUAL
FIELD_WITNESSES = af.FIELD_WITNESSES
#: The predecessor V1.0 witness sets (participants without the team-name witness), used only to check a legacy
#: sidecar's spans before refusing it as superseded.
LEGACY_FIELD_WITNESSES = {**af.FIELD_WITNESSES,
                          "a_participant": frozenset({"JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "JS_AWAY_TEAM_ID",
                                                      "AWAY_TEAM_HREF"}),
                          "b_participant": frozenset({"JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "JS_AWAY_TEAM_ID",
                                                      "AWAY_TEAM_HREF"})}
VERIFICATION = "SIDECAR_RAW_RECEIPT_FIELD_GRAIN_AND_PARTICIPANT_MAPPING_REDERIVATION_PASSED"
UTC = _dt.timezone.utc
TRUE, FALSE, UNKNOWN = base.TRUE, base.FALSE, base.UNKNOWN
NO_ARCHIVE = "NO_QUALIFIED_ARCHIVE_ASSERTION"
#: Capture record fields by the refusal they map to when the re-derived value differs.
CLOCK_FIELDS = ("clocks", "capture_id", "wayback_timestamp", "original_url")
RECEIPT_FIELDS = ("origin", "request_seq", "final_url", "http_status", "content_type", "memento_datetime_literal",
                  "origin_date_literal", "link_original", "archive_src", "payload_sha256", "payload_bytes",
                  "payload_path", "receipt_document", "receipt_document_sha256", "receipt_pointer")
PARTICIPANT_FIELDS = ("participant_mapping", "orientation", "page_participants")
#: A disposition field that differs from its reconstruction refuses with the code of the authority it derives from.
DISPOSITION_REFUSALS = (("parent", "ARCHIVE_DISPOSITION_PARENT_MISMATCH", "parent contest record and issued tranche"),
                        ("tranche", "ARCHIVE_DISPOSITION_TRANCHE_MISMATCH",
                         "issued tranche row (classification, stratum, selection role, locator, payload position)"),
                        ("receipts", "ARCHIVE_RECEIPT_ALTERED", "acquisition receipts"),
                        ("captures", "ARCHIVE_SEMANTIC_FORGERY", "key's complete expected capture collection"))


class ArchiveEvidenceError(base.SourceTimeQueryError):
    """A refused archive sidecar or archive query."""


def _refuse(code: str, message: str) -> ArchiveEvidenceError:
    return ArchiveEvidenceError(code, message)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cjson(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _multiset_difference(expected: list[Any], stored: list[Any]) -> dict[str, list[Any]]:
    want, have = collections.Counter(expected), collections.Counter(stored)
    return {"missing": sorted((want - have).elements(), key=str), "extra": sorted((have - want).elements(), key=str),
            "duplicated": sorted((k for k, n in have.items() if n > 1), key=str)}


# --------------------------------------------------------------------------------------------- issued authority

class IssuedAuthority:
    """One issued contract's authority: contract identity, the exact issued tranche bytes (rows, order, locators),
    the retained acquisition the contract binds, its parent source-time binding and its route control."""

    def __init__(self, *, contract_id: str, contract_sha256: str, tranche_bytes: bytes, tranche_sha256: str,
                 acquisition_identity: str, parent: dict[str, Any], control: dict[str, Any]) -> None:
        if _sha_bytes(tranche_bytes) != tranche_sha256:
            raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", "the issued tranche bytes do not hash to the contract's "
                                                           "tranche sha256")
        try:
            doc = json.loads(tranche_bytes.decode("utf-8"))
            rows = list(doc["selected"])
            keys = [str(r["contest_key"]) for r in rows]
        except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
            raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", f"issued tranche unreadable: {exc}") from exc
        if len(set(keys)) != len(keys) or doc.get("count") != len(keys) or not keys:
            raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", "issued tranche keys are not unique and counted")
        locators: dict[str, tuple[str, str]] = {}
        for row in rows:
            url = str(row.get("candidate_espn_url") or "")
            game = urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1]
            if not af.equivalent_original(url, game):
                raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", f"{row['contest_key']} candidate locator")
            locators[row["contest_key"]] = (url, game)
        controls = [r["contest_key"] for r in rows if r.get("selection_role") == af.CONTROL_ROLE]
        if controls != [control.get("contest_key")]:
            raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", "issued tranche and route control name different keys")
        self.contract_id, self.contract_sha256 = contract_id, contract_sha256
        self.tranche_sha256, self.acquisition_identity = tranche_sha256, acquisition_identity
        self.parent, self.control = parent, control
        self.keys = keys
        self.rows = {r["contest_key"]: r for r in rows}
        self.candidate_urls = {k: v[0] for k, v in locators.items()}
        self.game_ids = {k: v[1] for k, v in locators.items()}

    def binding(self) -> dict[str, Any]:
        return {"contract_id": self.contract_id, "contract_sha256": self.contract_sha256,
                "tranche_sha256": self.tranche_sha256, "acquisition_identity": self.acquisition_identity}


class ExpansionAuthority(IssuedAuthority):
    """The BAT-715 expansion's authority: the issued tranche bytes and the issued cohort bytes define the 97-key union
    (tranche order, then the cohort's new keys in cohort order), its rows and locators; the retained V1.2 acquisition
    and the expansion acquisition are the two receipt documents, in that order."""

    expansion = True

    def __init__(self, *, contract_id: str, contract_sha256: str, tranche_bytes: bytes, tranche_sha256: str,
                 cohort_bytes: bytes, cohort_sha256: str, acquisition_identity: str, retained_acquisition_identity: str,
                 retained_policy_id: str, parent: dict[str, Any], control: dict[str, Any]) -> None:
        super().__init__(contract_id=contract_id, contract_sha256=contract_sha256, tranche_bytes=tranche_bytes,
                         tranche_sha256=tranche_sha256, acquisition_identity=acquisition_identity, parent=parent,
                         control=control)
        if _sha_bytes(cohort_bytes) != cohort_sha256:
            raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", "the issued cohort bytes do not hash to the contract's cohort "
                                                           "sha256")
        try:
            doc = json.loads(cohort_bytes.decode("utf-8"))
            crows = list(doc["selected"])
            ckeys = [str(r["contest_key"]) for r in crows]
        except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
            raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", f"issued cohort unreadable: {exc}") from exc
        if len(set(ckeys)) != len(ckeys) or not ckeys or (doc.get("counts") or {}).get("new_query_keys") != len(ckeys):
            raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", "issued cohort keys are not unique and counted")
        tranche_keys = list(self.keys)
        rows = {k: {**r, "selection_sources": ["TRANCHE_28"]} for k, r in self.rows.items()}
        for row in crows:
            key = row["contest_key"]
            url = str(row.get("candidate_espn_url") or "")
            game = urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1]
            if not af.equivalent_original(url, game):
                raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", f"{key} candidate locator")
            if key in rows:
                old = rows[key]
                if (old["candidate_espn_url"], old["contest_date"], old["a_key"], old["b_key"], old["cfbd_game_id"]) != (
                        url, row["contest_date"], row["a_key"], row["b_key"], row["cfbd_game_id"]) or \
                        not row.get("already_in_original_tranche"):
                    raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", f"{key}: tranche and cohort rows disagree")
                old["selection_sources"] = ["TRANCHE_28", "COHORT_70"]
                continue
            if row.get("already_in_original_tranche"):
                raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", f"{key}: cohort says tranche, tranche disagrees")
            rows[key] = {"contest_key": key, "season": None, "contest_date": row["contest_date"],
                         "a_key": row["a_key"], "b_key": row["b_key"], "cfbd_game_id": row["cfbd_game_id"],
                         "classification_pair": None, "stratum": af.COHORT_STRATUM, "selection_role": af.COHORT_ROLE,
                         "candidate_espn_url": url, "selection_sources": ["COHORT_70"]}
            self.candidate_urls[key], self.game_ids[key] = url, game
        self.tranche_keys, self.cohort_keys = tranche_keys, ckeys
        self.keys = tranche_keys + [k for k in ckeys if k not in set(tranche_keys)]
        self.rows = rows
        self.cohort_sha256 = cohort_sha256
        self.retained_acquisition_identity, self.retained_policy_id = retained_acquisition_identity, retained_policy_id

    def binding(self) -> dict[str, Any]:
        return {**super().binding(), "cohort_sha256": self.cohort_sha256,
                "retained_acquisition_identity": self.retained_acquisition_identity}


_REGISTERED: list[IssuedAuthority] = []


def packaged_authority() -> IssuedAuthority:
    """The issued authority this package serves: contract V1.2 and its packaged exact tranche bytes."""
    path = Path(__file__).with_name(ISSUED_TRANCHE_FILE)
    if not path.is_file():
        raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", f"the packaged issued tranche {path.name} is missing")
    return IssuedAuthority(tranche_bytes=path.read_bytes(), **ISSUED_V1_2)


def packaged_expansion_authority() -> ExpansionAuthority | None:
    """The issued BAT-715 expansion authority (packaged tranche and cohort bytes), once it is issued."""
    if ISSUED_EXPANSION is None:
        return None
    tranche = Path(__file__).with_name(ISSUED_TRANCHE_FILE)
    cohort = Path(__file__).with_name(ISSUED_COHORT_FILE)
    if not tranche.is_file() or not cohort.is_file():
        raise _refuse("ARCHIVE_AUTHORITY_UNAVAILABLE", "the packaged issued tranche or cohort is missing")
    return ExpansionAuthority(tranche_bytes=tranche.read_bytes(), cohort_bytes=cohort.read_bytes(), **ISSUED_EXPANSION)


@contextlib.contextmanager
def registered_authority(authority: IssuedAuthority) -> Iterator[IssuedAuthority]:
    """In-process development and test hook: accept one further issued authority (for example a synthetic fixture
    world's contract, tranche and acquisition) for the duration of the block. The console and module entry points
    never register anything; they serve only the packaged issued authority."""
    _REGISTERED.append(authority)
    try:
        yield authority
    finally:
        _REGISTERED.remove(authority)


def issued_authority(contract_sha256: Any, acquisition_identity: Any) -> IssuedAuthority:
    packaged = [packaged_authority()]
    if ISSUED_EXPANSION is not None and ISSUED_EXPANSION.get("contract_sha256") == contract_sha256:
        packaged.append(packaged_expansion_authority())
    candidates = [a for a in [*packaged, *_REGISTERED] if a.contract_sha256 == contract_sha256]
    if not candidates:
        raise _refuse("ARCHIVE_CONTRACT_NOT_ISSUED", f"contract sha256 {contract_sha256!r} is not an issued contract "
                                                     "this consumer serves")
    for authority in reversed(candidates):
        if authority.acquisition_identity == acquisition_identity:
            return authority
    raise _refuse("ARCHIVE_ACQUISITION_NOT_ISSUED", f"acquisition {acquisition_identity!r} is not the retained "
                                                    "acquisition the issued contract binds")


# --------------------------------------------------------------------------------------------- sidecar verification

def verify_archive_database(database: Path, *, expect_identity: str | None = None) -> dict[str, Any]:
    db = Path(database)
    if not db.is_file():
        raise _refuse("ARCHIVE_DATABASE_MISSING", f"no archive sidecar at {db}")
    if db.name != ARCHIVE_DB_FILE or db.resolve().parent.parent.name != "sha256":
        raise _refuse("ARCHIVE_LOCATION_INVALID", "the sidecar must sit at <root>/sha256/<id>/" + ARCHIVE_DB_FILE)
    identity = db.resolve().parent.name
    if not base.IDENTITY_RE.match(identity):
        raise _refuse("ARCHIVE_LOCATION_INVALID", f"directory name {identity!r} is not a SHA-256 identity")
    manifest_path = base.manifest_path_for(db)
    if not manifest_path.is_file():
        raise _refuse("ARCHIVE_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity_document = document["identity_document"]
        computed = hashlib.sha256(base.canonical_json_bytes(identity_document)).hexdigest()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _refuse("ARCHIVE_MANIFEST_MALFORMED", str(exc)) from exc
    if computed != identity or document.get("identity") != identity:
        raise _refuse("ARCHIVE_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                   f"{identity}")
    schemas = (identity_document.get("stage"), identity_document.get("schema"), identity_document.get("db_schema_version"))
    if schemas not in (("archived-publication-database", ARCHIVE_DOCUMENT_SCHEMA, ARCHIVE_DB_SCHEMA),
                       ("archived-publication-database", LEGACY_DOCUMENT_SCHEMA, LEGACY_DB_SCHEMA),
                       ("archived-publication-database", EXPANSION_DOCUMENT_SCHEMA, EXPANSION_DB_SCHEMA)):
        raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", "the manifest is not a known archived-publication sidecar")
    expected = (identity_document.get("outputs") or {}).get(ARCHIVE_DB_FILE)
    actual = base._sha256_file(db)
    if expected != actual:
        raise _refuse("ARCHIVE_DATABASE_TAMPERED", f"sidecar bytes hash to {actual}, manifest names {expected}")
    if expect_identity is not None and expect_identity != identity:
        raise _refuse("STALE_ARCHIVE_IDENTITY", f"expected {expect_identity}, found {identity}")
    return {"archive_identity": identity, "archive_sha256": actual, "manifest": str(manifest_path),
            "content_identity": identity_document.get("content_identity"),
            "contract_sha256": identity_document.get("contract_sha256"), "parent": identity_document.get("parent"),
            "table_counts": identity_document.get("table_counts"),
            "record_counts": identity_document.get("record_counts"),
            "db_schema_version": identity_document.get("db_schema_version")}


class ArchiveEvidence:
    """A verified, read-only archive sidecar composed with one verified source-time database."""

    def __init__(self, database: Path, source: base.SourceTimeDatabase, *, expect_identity: str | None = None) -> None:
        self.binding = verify_archive_database(database, expect_identity=expect_identity)
        self.source = source
        self.root = Path(database).resolve().parent.parent.parent
        conn = base.connect_readonly(database)
        try:
            meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
            counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
            tables = {t: [json.loads(row["record"]) for row in conn.execute(f"SELECT record FROM {t} ORDER BY ord")]
                      for t in TABLES if t != "meta"}
        except sqlite3.DatabaseError as exc:
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", str(exc)) from exc
        finally:
            conn.close()
        legacy = (meta.get("schema_version"), meta.get("contract_id")) in \
            ((LEGACY_DB_SCHEMA, c) for c in LEGACY_CONTRACT_IDS)
        superseded = meta.get("schema_version") == ARCHIVE_DB_SCHEMA and meta.get("contract_id") in \
            SUPERSEDED_CONTRACT_IDS
        expansion = meta.get("schema_version") == EXPANSION_DB_SCHEMA and meta.get("contract_id") in \
            EXPANSION_CONTRACT_IDS
        if not legacy and not superseded and not expansion and (meta.get("schema_version") != ARCHIVE_DB_SCHEMA or
                                                                meta.get("contract_id") not in KNOWN_CONTRACT_IDS):
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r} contract "
                                                        f"{meta.get('contract_id')!r}")
        if legacy != (self.binding["db_schema_version"] == LEGACY_DB_SCHEMA) or \
                expansion != (self.binding["db_schema_version"] == EXPANSION_DB_SCHEMA):
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", "sidecar meta and manifest schemas differ")
        self.expansion = expansion
        self.row_labels = EXPANSION_ROW_LABELS if expansion else ARCHIVE_ROW_LABELS
        if meta.get("content_identity") != self.binding["content_identity"] or \
                meta.get("contract_sha256") != self.binding["contract_sha256"] or \
                json.loads(meta.get("parent") or "null") != self.binding["parent"]:
            raise _refuse("ARCHIVE_IDENTITY_MISMATCH", "sidecar meta and manifest identities differ")
        records = {name: counts[table] for name, table in PAYLOADS.items()}
        if counts != self.binding["table_counts"] or records != self.binding["record_counts"]:
            raise _refuse("ARCHIVE_COUNT_MISMATCH", f"counts {counts} differ from the manifest")
        if json.loads(meta.get("row_labels") or "null") != self.row_labels:
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", "row labels differ from the archive evidence-only labels")
        parent = (self.binding["parent"] or {}).get("source_time") or {}
        if (parent.get("database_identity"), parent.get("sqlite_sha256"), parent.get("content_identity"),
                parent.get("contract_sha256")) != (source.binding["database_identity"], source.binding["database_sha256"],
                                                   source.binding["content_identity"], source.binding["contract_sha256"]):
            raise _refuse("ARCHIVE_PARENT_MISMATCH", "the sidecar was built over another source-time database")
        self.meta = meta
        self.dispositions = tables["dispositions"]
        self.requests = tables["requests"]
        self.captures = tables["captures"]
        self.assertions = tables["assertions"]
        self._extractions: dict[str, dict[str, Any]] = {}
        if legacy:
            self._refuse_legacy()
        if superseded:
            self._refuse_superseded()
        self.authority = issued_authority(self.binding["contract_sha256"], meta.get("acquisition_identity"))
        if bool(getattr(self.authority, "expansion", False)) != expansion:
            raise _refuse("ARCHIVE_CONTRACT_NOT_ISSUED", "the sidecar schema and the issued authority's kind differ")
        self._check_authority()
        if expansion:
            self._verify_expansion()
        else:
            self._verify()
        self.by_key = {d["contest_key"]: d for d in self.dispositions}
        self.captures_by_id = {c["capture_id"]: c for c in self.captures}

    def close(self) -> None:
        return None

    def __enter__(self) -> "ArchiveEvidence":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ verification
    def _raw(self, sha: Any) -> bytes:
        if not isinstance(sha, str) or not base.IDENTITY_RE.match(sha):
            raise _refuse("ARCHIVE_PATH_INVALID", f"raw reference {sha!r}")
        path = self.root / "raw" / "sha256" / sha
        if not path.is_file():
            raise _refuse("ARCHIVE_RAW_MISSING", f"raw payload {sha} is missing")
        data = path.read_bytes()
        if _sha_bytes(data) != sha:
            raise _refuse("ARCHIVE_RAW_ALTERED", f"raw payload {sha} bytes changed")
        return data

    def _occurrences(self, payload_sha: str, payload: bytes) -> set[tuple[str, int, int, str]]:
        if payload_sha not in self._extractions:
            self._extractions[payload_sha] = af.extract(payload)
        return {(w["witness"], w["span"][0], w["span"][1], w["literal"])
                for w in self._extractions[payload_sha]["witnesses"]}

    def _check_assertion_structure(self, payloads: dict[str, bytes], field_witnesses: dict[str, Any]) -> None:
        """Natural keys, ownership, field/witness role and the exact-occurrence rule for every stored witness."""
        seen = set()
        captures = {c["capture_id"]: c for c in self.captures}
        for item in self.assertions:
            natural = (item["contest_key"], item["original_url"], item["capture_id"], item["payload_sha256"],
                       item["field"], item["witness"], item["source_revision"], tuple(item["witness_span"]))
            if natural in seen:
                raise _refuse("ARCHIVE_DUPLICATE_ASSERTION", f"duplicate assertion {natural[:7]}")
            seen.add(natural)
            cap = captures.get(item["capture_id"])
            if cap is None or cap["contest_key"] != item["contest_key"] or cap["payload_sha256"] != item[
                    "payload_sha256"] or item["source_revision"] != cap["capture_id"] or \
                    item["original_url"] != cap["original_url"] or cap["capture_id"] not in payloads:
                raise _refuse("ARCHIVE_SOURCE_INVALID", "assertion does not belong to its capture")
            if item["field"] not in FIELDS or item["witness"] not in field_witnesses[item["field"]] or \
                    item.get("field_role") != base.ROLES[item["field"]]:
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"{item['field']} cannot be witnessed by {item['witness']}")
            span = item["witness_span"]
            if not (isinstance(span, list) and len(span) == 2 and all(isinstance(x, int) for x in span)) or \
                    (item["witness"], span[0], span[1], str(item["literal"])) not in self._occurrences(
                        cap["payload_sha256"], payloads[cap["capture_id"]]):
                raise _refuse("ARCHIVE_WITNESS_MISMATCH", f"{item['capture_id']} {item['field']} {item['witness']} "
                                                          f"{span} is not an occurrence of that witness in the raw page")

    def _refuse_legacy(self) -> None:
        """A V1.0 sidecar: check that every stored witness span is an exact occurrence, then refuse it as superseded
        (it orients participants by equal numeric ids in two namespaces and cannot be served under V1.2)."""
        payloads = {}
        for cap in self.captures:
            payloads[cap["capture_id"]] = self._raw(cap["payload_sha256"])
        self._check_assertion_structure(payloads, LEGACY_FIELD_WITNESSES)
        raise _refuse("ARCHIVE_SCHEMA_SUPERSEDED", "contract V1.0 sidecar: its witness spans are exact occurrences but "
                                                   "it carries no evidenced participant mapping (numeric ESPN/CFBD "
                                                   "equality); use the V1.2 successor")

    def _refuse_superseded(self) -> None:
        """A V1.1 sidecar: check that every stored witness span is an exact occurrence, then refuse it as superseded
        (V1.1 left a version with an unresolved participant mapping qualified for its date and completion)."""
        payloads = {}
        for cap in self.captures:
            payloads[cap["capture_id"]] = self._raw(cap["payload_sha256"])
        self._check_assertion_structure(payloads, FIELD_WITNESSES)
        raise _refuse("ARCHIVE_SCHEMA_SUPERSEDED", "contract V1.1 sidecar: its witness spans are exact occurrences but "
                                                   "it did not quarantine a version whose participants do not map; use "
                                                   "the V1.2 successor")

    def _check_authority(self) -> None:
        """The sidecar names exactly the issued contract, tranche, parent and route control (the acquisition identity
        was matched when the authority was resolved)."""
        auth = self.authority
        if self.meta.get("contract_id") != auth.contract_id:
            raise _refuse("ARCHIVE_CONTRACT_NOT_ISSUED", f"contract id {self.meta.get('contract_id')!r} is not the issued "
                                                         f"{auth.contract_id}")
        if self.meta.get("tranche_sha256") != auth.tranche_sha256:
            raise _refuse("ARCHIVE_TRANCHE_NOT_ISSUED", "the sidecar names another tranche than the issued one")
        if self.binding["parent"] != auth.parent:
            raise _refuse("ARCHIVE_PARENT_MISMATCH", "the sidecar's parent is not the issued contract's parent")
        if json.loads(self.meta.get("control") or "null") != auth.control:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "control binding differs from the issued route control")
        if self.expansion:
            if self.meta.get("cohort_sha256") != auth.cohort_sha256:
                raise _refuse("ARCHIVE_TRANCHE_NOT_ISSUED", "the sidecar names another cohort than the issued one")
            expected = [{"acquisition_identity": auth.retained_acquisition_identity,
                         "policy_id": auth.retained_policy_id, "origin": RETAINED_ORIGIN},
                        {"acquisition_identity": auth.acquisition_identity,
                         "policy_id": self.meta.get("acquisition_policy_id"), "origin": EXPANSION_ORIGIN}]
            if json.loads(self.meta.get("acquisitions") or "null") != expected:
                raise _refuse("ARCHIVE_ACQUISITION_NOT_ISSUED", "the sidecar's acquisitions are not the issued retained "
                                                                "and expansion acquisitions in order")

    def _acquisition(self, ident: str) -> dict[str, Any]:
        path = self.root / "acquisition" / "sha256" / ident / "acquisition.json"
        if not path.is_file():
            raise _refuse("ARCHIVE_RAW_MISSING", f"acquisition document {ident} is missing")
        data = path.read_bytes()
        if _sha_bytes(data) != ident:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"acquisition document {ident} bytes changed")
        doc = json.loads(data.decode("utf-8"))
        if doc.get("schema") != ACQUISITION_SCHEMA:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"acquisition document {ident} schema")
        return doc

    def _verify_expansion(self) -> None:
        """The BAT-715 union: both receipt documents, every request of both, the complete expected capture collection
        (duplicate rule applied), every capture/assertion re-derived and every disposition reconstructed."""
        auth = self.authority
        retained = self._acquisition(auth.retained_acquisition_identity)
        current = self._acquisition(auth.acquisition_identity)
        if (retained.get("policy_id"), retained.get("tranche_sha256"), retained.get("keys")) != (
                auth.retained_policy_id, auth.tranche_sha256, auth.tranche_keys):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "retained acquisition binding")
        if (current.get("policy_id"), current.get("tranche_sha256"), current.get("keys")) != (
                self.meta.get("acquisition_policy_id"), auth.cohort_sha256, auth.cohort_keys):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "expansion acquisition binding")
        control = auth.control
        receipt_raw = self._raw(control.get("raw_receipt_sha256"))
        receipt = json.loads(receipt_raw.decode("utf-8"))
        self._raw(control.get("route_qualification_sha256"))
        for doc in (retained, current):
            if doc.get("control") != {**control, "requests": 0}:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", "control binding differs from an acquisition document")
        acquisitions = [(auth.retained_acquisition_identity, retained), (auth.acquisition_identity, current)]
        stored_keys = [d.get("contest_key") for d in self.dispositions]
        if stored_keys != auth.keys:
            if collections.Counter(stored_keys) == collections.Counter(auth.keys):
                raise _refuse("ARCHIVE_RECORD_ORDER_MISMATCH", "dispositions are not in the issued union order")
            raise _refuse("ARCHIVE_DISPOSITION_COLLECTION_MISMATCH", f"dispositions are not exactly one per issued union "
                                                                     f"key: {_multiset_difference(auth.keys, stored_keys)}")
        # ---- requests: both acquisitions' receipts in payload order, each with its acquisition identity
        ordered = [(ident, r) for key in auth.keys for ident, doc in acquisitions for r in doc["requests"]
                   if r.get("contest_key") == key]
        if len(ordered) != sum(len(doc["requests"]) for _, doc in acquisitions) or len(self.requests) != len(ordered):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "request accounting differs from the acquisition documents")
        stored_ids = [(r.get("acquisition_identity"), r.get("seq")) for r in self.requests]
        expected_ids = [(ident, r["seq"]) for ident, r in ordered]
        if stored_ids != expected_ids:
            if collections.Counter(stored_ids) == collections.Counter(expected_ids):
                raise _refuse("ARCHIVE_RECORD_ORDER_MISMATCH", "requests are not in the payload order")
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"request accounting differs from the acquisition documents: "
                                                     f"{_multiset_difference(expected_ids, stored_ids)}")
        for mine, (ident, theirs) in zip(self.requests, ordered):
            expected = af.expansion_request_record(ident, theirs, auth.game_ids[theirs["contest_key"]], self._raw)
            receipt_mine = {k: v for k, v in mine.items() if k not in af.REQUEST_DERIVED}
            receipt_expected = {k: v for k, v in expected.items() if k not in af.REQUEST_DERIVED}
            if _cjson(receipt_mine) != _cjson(receipt_expected):
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"request {ident[:12]}/{mine.get('seq')} differs from its "
                                                         f"receipt")
            host = (urllib.parse.urlsplit(str(mine["url"])).hostname or "").lower()
            if host not in ("archive.org", "web.archive.org") or (mine["kind"] == "METADATA") != (host == "archive.org"):
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"request {mine['seq']} host {host}")
            derived = [k for k in af.REQUEST_DERIVED if k not in mine or _cjson(mine[k]) != _cjson(expected[k])]
            if derived:
                raise _refuse("ARCHIVE_REQUEST_DERIVATION_MISMATCH",
                              f"request {mine['seq']} {derived} differ from the derivation from its raw receipt and "
                              f"retained body")
            if mine.get("body_sha256"):
                self._raw(mine["body_sha256"])
        # ---- captures: the complete expected collection (duplicate rule applied) before any per-capture check
        control_sha = _sha_bytes(receipt_raw)
        versions: list[dict[str, Any]] = []
        duplicates: dict[str, list[dict[str, Any]]] = {}
        for key in auth.keys:
            control_version = None
            if auth.rows[key].get("selection_role") == af.CONTROL_ROLE:
                control_version = af.control_version(control_sha, receipt, self._raw(control["payload_sha256"]))
            entries, dups = af.expansion_versions(key, control_version, acquisitions, self._raw)
            duplicates[key] = dups
            versions += af.order_captures(entries)
        for cap in self.captures:
            if cap.get("contest_key") not in auth.rows:
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"capture for out-of-union key {cap.get('contest_key')}")
        expected_caps = [v["capture_id"] for v in versions]
        stored_caps = [c.get("capture_id") for c in self.captures]
        if stored_caps != expected_caps:
            if collections.Counter(stored_caps) == collections.Counter(expected_caps):
                raise _refuse("ARCHIVE_RECORD_ORDER_MISMATCH", "captures are not in the payload order")
            raise _refuse("ARCHIVE_CAPTURE_COLLECTION_MISMATCH",
                          f"stored captures differ from the expected collection (the retained control plus every "
                          f"distinct receipted replayed version of both acquisitions, quarantined versions included): "
                          f"{_multiset_difference(expected_caps, stored_caps)}")
        payloads: dict[str, bytes] = {}
        for version, cap in zip(versions, self.captures):
            payload = version["payload"]
            payloads[cap["capture_id"]] = payload
            if cap.get("payload_path") != af.raw_rel(version["payload_sha256"]) or cap.get("payload_bytes") != len(payload):
                raise _refuse("ARCHIVE_PATH_INVALID", f"capture {cap['capture_id']} payload path")
        self._check_assertion_structure(payloads, FIELD_WITNESSES)
        parents: dict[str, dict[str, Any]] = {}
        stored_rows: dict[str, list[dict[str, Any]]] = {}
        for item in self.assertions:
            stored_rows.setdefault(item["capture_id"], []).append(item)
        derived_caps: dict[str, list[dict[str, Any]]] = {}
        expected_assertions: list[dict[str, Any]] = []
        for version, cap in zip(versions, self.captures):
            key = version["contest_key"]
            if key not in parents:
                parents[key] = self._parent(key)
            expected, rows = af.derive_capture(key, parents[key], auth.game_ids[key], version["version"],
                                               version["payload_sha256"])
            self._compare_capture(cap, expected)
            self._compare_rows(cap["capture_id"], stored_rows.get(cap["capture_id"], []), rows)
            derived_caps.setdefault(key, []).append(expected)
            expected_assertions += rows
        if [_cjson(a) for a in self.assertions] != [_cjson(a) for a in expected_assertions]:
            raise _refuse("ARCHIVE_RECORD_ORDER_MISMATCH", "assertion rows are not in the payload order")
        conflicts = af.mapping_conflicts(self.captures)
        if conflicts:
            raise _refuse("ARCHIVE_PARTICIPANT_MAPPING_CONTRADICTORY", f"qualified participant mappings disagree: "
                                                                        f"{conflicts[:3]}")
        # ---- dispositions: every record reconstructed from the scope rows, the parent, both receipts and captures
        for index, (key, stored) in enumerate(zip(auth.keys, self.dispositions)):
            if key not in parents:
                parents[key] = self._parent(key)
            parent = parents[key]
            row, record = dict(auth.rows[key]), parent["record"]
            tranche_row = "TRANCHE_28" in row["selection_sources"]
            if row["season"] is None:
                row["season"] = record["season"]
            if (row.get("season"), row.get("contest_date"), row.get("a_key"), row.get("b_key"),
                    (row.get("cfbd_game_id") or {}).get("value")) != (
                    record["season"], record["contest_date"], record["a_key"], record["b_key"],
                    (record.get("cfbd_game_id") or {}).get("value")) or (tranche_row and (
                    row.get("a_points"), row.get("b_points")) != (parent["values"]["a_points"],
                                                                  parent["values"]["b_points"])):
                raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{key}: the issued scope row differs from the opened parent "
                                                         f"contest")
            mine = [r for _, doc in acquisitions for r in doc["requests"] if r["contest_key"] == key]
            outcomes = [{"acquisition_identity": ident, "acquisition_outcome": (doc.get("outcomes") or {}).get(key)}
                        for ident, doc in acquisitions if key in (doc.get("outcomes") or {})]
            if not outcomes:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{key} has no acquisition outcome")
            expected = af.expansion_disposition_record(index, key, row, auth.candidate_urls[key], auth.game_ids[key],
                                                       outcomes, mine, derived_caps.get(key, []), duplicates[key],
                                                       parent["values"])
            self._compare_disposition(key, stored, expected, af.EXPANSION_DISPOSITION_AUTHORITY)

    def _verify(self) -> None:
        auth = self.authority
        acq_id = auth.acquisition_identity
        acq_path = self.root / "acquisition" / "sha256" / acq_id / "acquisition.json"
        if not acq_path.is_file():
            raise _refuse("ARCHIVE_RAW_MISSING", "acquisition document is missing")
        acq_bytes = acq_path.read_bytes()
        if _sha_bytes(acq_bytes) != acq_id:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "acquisition document bytes changed")
        acquisition = json.loads(acq_bytes.decode("utf-8"))
        if acquisition.get("schema") != ACQUISITION_SCHEMA or \
                acquisition.get("policy_id") != self.meta.get("acquisition_policy_id") or \
                acquisition.get("tranche_sha256") != auth.tranche_sha256:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "acquisition document binding")
        control = auth.control
        receipt_raw = self._raw(control.get("raw_receipt_sha256"))
        receipt = json.loads(receipt_raw.decode("utf-8"))
        self._raw(control.get("route_qualification_sha256"))
        if acquisition.get("control") != {**control, "requests": 0}:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "control binding differs from the acquisition document")
        if acquisition.get("keys") != auth.keys:
            raise _refuse("ARCHIVE_TRANCHE_NOT_ISSUED", "the acquisition document's keys are not the issued tranche")
        # ---- dispositions: exactly one per issued tranche key, in tranche order
        stored_keys = [d.get("contest_key") for d in self.dispositions]
        if stored_keys != auth.keys:
            if collections.Counter(stored_keys) == collections.Counter(auth.keys):
                raise _refuse("ARCHIVE_RECORD_ORDER_MISMATCH", "dispositions are not in the issued tranche order")
            raise _refuse("ARCHIVE_DISPOSITION_COLLECTION_MISMATCH", f"dispositions are not exactly one per issued "
                                                                     f"tranche key: "
                                                                     f"{_multiset_difference(auth.keys, stored_keys)}")
        # ---- requests: the acquisition receipts in payload order plus their re-derived path and answer
        self._verify_requests(acquisition["requests"])
        # ---- captures: the complete expected collection before any per-capture check
        versions = self._expected_versions(acquisition, acq_id, receipt, _sha_bytes(receipt_raw))
        for cap in self.captures:
            if cap.get("contest_key") not in auth.rows:
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"capture for out-of-tranche key {cap.get('contest_key')}")
        expected_ids = [v["capture_id"] for v in versions]
        stored_ids = [c.get("capture_id") for c in self.captures]
        if stored_ids != expected_ids:
            if collections.Counter(stored_ids) == collections.Counter(expected_ids):
                raise _refuse("ARCHIVE_RECORD_ORDER_MISMATCH", "captures are not in the payload order")
            raise _refuse("ARCHIVE_CAPTURE_COLLECTION_MISMATCH",
                          f"stored captures differ from the expected collection (the retained control plus every "
                          f"receipted replayed version, quarantined versions included): "
                          f"{_multiset_difference(expected_ids, stored_ids)}")
        payloads: dict[str, bytes] = {}
        for version, cap in zip(versions, self.captures):
            payload = version["payload"]
            payloads[cap["capture_id"]] = payload
            if cap.get("payload_path") != af.raw_rel(version["payload_sha256"]) or cap.get("payload_bytes") != len(payload):
                raise _refuse("ARCHIVE_PATH_INVALID", f"capture {cap['capture_id']} payload path")
        self._check_assertion_structure(payloads, FIELD_WITNESSES)
        parents: dict[str, dict[str, Any]] = {}
        stored_rows: dict[str, list[dict[str, Any]]] = {}
        for item in self.assertions:
            stored_rows.setdefault(item["capture_id"], []).append(item)
        derived: dict[str, list[dict[str, Any]]] = {}
        expected_assertions: list[dict[str, Any]] = []
        for version, cap in zip(versions, self.captures):
            key = version["contest_key"]
            if key not in parents:
                parents[key] = self._parent(key)
            expected, rows = af.derive_capture(key, parents[key], auth.game_ids[key], version["version"],
                                               version["payload_sha256"])
            self._compare_capture(cap, expected)
            self._compare_rows(cap["capture_id"], stored_rows.get(cap["capture_id"], []), rows)
            derived.setdefault(key, []).append(expected)
            expected_assertions += rows
        if [_cjson(a) for a in self.assertions] != [_cjson(a) for a in expected_assertions]:
            raise _refuse("ARCHIVE_RECORD_ORDER_MISMATCH", "assertion rows are not in the payload order")
        conflicts = af.mapping_conflicts(self.captures)
        if conflicts:
            raise _refuse("ARCHIVE_PARTICIPANT_MAPPING_CONTRADICTORY", f"qualified participant mappings disagree: "
                                                                        f"{conflicts[:3]}")
        # ---- dispositions: every record reconstructed from its authorities
        for index, (key, stored) in enumerate(zip(auth.keys, self.dispositions)):
            if key not in parents:
                parents[key] = self._parent(key)
            parent = parents[key]
            row, record = auth.rows[key], parent["record"]
            if (row.get("season"), row.get("contest_date"), row.get("a_key"), row.get("b_key"),
                    (row.get("cfbd_game_id") or {}).get("value"), row.get("a_points"), row.get("b_points")) != (
                    record["season"], record["contest_date"], record["a_key"], record["b_key"],
                    (record.get("cfbd_game_id") or {}).get("value"), parent["values"]["a_points"],
                    parent["values"]["b_points"]):
                raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{key}: the issued tranche row differs from the opened parent "
                                                         f"contest")
            mine = [r for r in acquisition["requests"] if r["contest_key"] == key]
            expected = af.disposition_record(index, key, row, auth.candidate_urls[key], auth.game_ids[key],
                                             (acquisition.get("outcomes") or {}).get(key), mine, derived.get(key, []),
                                             parent["values"])
            self._compare_disposition(key, stored, expected)

    def _verify_requests(self, acquisition_requests: list[dict[str, Any]]) -> None:
        auth = self.authority
        ordered = [r for key in auth.keys for r in acquisition_requests if r.get("contest_key") == key]
        if len(ordered) != len(acquisition_requests) or len(self.requests) != len(ordered):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "request accounting differs from the acquisition document")
        stored_seqs, expected_seqs = [r.get("seq") for r in self.requests], [r["seq"] for r in ordered]
        if stored_seqs != expected_seqs:
            if collections.Counter(stored_seqs) == collections.Counter(expected_seqs):
                raise _refuse("ARCHIVE_RECORD_ORDER_MISMATCH", "requests are not in the payload order")
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"request accounting differs from the acquisition document: "
                                                     f"{_multiset_difference(expected_seqs, stored_seqs)}")
        for mine, theirs in zip(self.requests, ordered):
            expected = af.request_record(theirs, auth.game_ids[theirs["contest_key"]], self._raw)
            receipt_mine = {k: v for k, v in mine.items() if k not in af.REQUEST_DERIVED}
            receipt_expected = {k: v for k, v in expected.items() if k not in af.REQUEST_DERIVED}
            if _cjson(receipt_mine) != _cjson(receipt_expected):
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"request {mine.get('seq')} differs from its receipt")
            host = (urllib.parse.urlsplit(str(mine["url"])).hostname or "").lower()
            if host not in ("archive.org", "web.archive.org") or (mine["kind"] == "METADATA") != (host == "archive.org"):
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"request {mine['seq']} host {host}")
            derived = [k for k in af.REQUEST_DERIVED if k not in mine or _cjson(mine[k]) != _cjson(expected[k])]
            if derived:
                raise _refuse("ARCHIVE_REQUEST_DERIVATION_MISMATCH",
                              f"request {mine['seq']} {derived} differ from the derivation from its raw receipt and "
                              f"retained body")
            if mine.get("body_sha256"):
                self._raw(mine["body_sha256"])

    def _expected_versions(self, acquisition: dict[str, Any], acq_id: str, receipt: dict[str, Any],
                           receipt_sha: str) -> list[dict[str, Any]]:
        """Every archived version the receipts establish, in payload order: per issued tranche key, the retained
        control and each receipted replayed version (af.capture_request), ordered by capture timestamp and payload."""
        auth = self.authority
        out: list[dict[str, Any]] = []
        for key in auth.keys:
            versions = []
            if auth.rows[key].get("selection_role") == af.CONTROL_ROLE:
                versions.append(af.control_version(receipt_sha, receipt, self._raw(auth.control["payload_sha256"])))
            for index, request in enumerate(acquisition["requests"]):
                if request["contest_key"] == key and af.capture_request(request):
                    versions.append(af.worker_version(acq_id, index, request, self._raw(request["body_sha256"])))
            entries = []
            for version in versions:
                payload_sha = _sha_bytes(version["payload"])
                capture_id, timestamp = af.capture_identity(version["final_url"], payload_sha)
                entries.append({"contest_key": key, "version": version, "payload": version["payload"],
                                "payload_sha256": payload_sha, "capture_id": capture_id, "wayback_timestamp": timestamp})
            out += af.order_captures(entries)
        return out

    def _parent(self, key: str) -> dict[str, Any]:
        contest = self.source.contest(key)
        if contest is None:
            raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{key} is not a source-time contest")
        values: dict[str, set[str]] = {}
        for item in contest["assertions"]:
            values.setdefault(item["field"], set()).add(_cjson(item["parent_value"]))
        if set(values) != set(FIELDS) or any(len(v) != 1 for v in values.values()):
            raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{key} parent values are not single")
        row = self.source.conn.execute("SELECT lineage FROM contests WHERE contest_key = ?", (key,)).fetchone()
        lineage = base._unpack(row["lineage"]) if row is not None and row["lineage"] is not None else []
        record = contest["record"]
        return {"record": record, "values": {f: json.loads(next(iter(values[f]))) for f in FIELDS},
                "participants": af.participant_sources(record, lineage)}

    @staticmethod
    def _compare_capture(stored: dict[str, Any], expected: dict[str, Any]) -> None:
        cid = stored.get("capture_id")
        if set(stored) != set(expected):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cid} record fields {sorted(set(stored) ^ set(expected))}")
        differs = [k for k in expected if _cjson(stored[k]) != _cjson(expected[k])]
        if not differs:
            return
        if any(k in RECEIPT_FIELDS for k in differs):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cid} receipt literals {[k for k in differs if k in RECEIPT_FIELDS]}")
        if any(k in CLOCK_FIELDS for k in differs):
            raise _refuse("ARCHIVE_CLOCK_FORGED", f"{cid} {[k for k in differs if k in CLOCK_FIELDS]}")
        if "main_element_spans" in differs:
            raise _refuse("ARCHIVE_WITNESS_OUT_OF_SCOPE", f"{cid} main element scopes differ from the raw page")
        participant_states = any(stored["field_states"].get(f) != expected["field_states"].get(f)
                                 for f in ("a_participant", "b_participant"))
        if any(k in PARTICIPANT_FIELDS for k in differs) or participant_states:
            raise _refuse("ARCHIVE_PARTICIPANT_MAPPING_INVALID", f"{cid} participant mapping, orientation or "
                                                                 f"participant states differ from the evidence")
        raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cid} {differs} differ from the re-derived version")

    @staticmethod
    def _compare_rows(capture_id: str, stored: list[dict[str, Any]], expected: list[dict[str, Any]]) -> None:
        if [_cjson(r) for r in stored] == [_cjson(r) for r in expected]:
            return
        have = sorted((r["witness"], tuple(r["witness_span"])) for r in stored)
        want = sorted((r["witness"], tuple(r["witness_span"])) for r in expected)
        if have != want:
            missing = sorted(set(want) - set(have))
            extra = sorted(set(have) - set(want))
            raise _refuse("ARCHIVE_WITNESS_SET_MISMATCH", f"{capture_id} witness rows omitted {missing[:4]} or "
                                                          f"unexpected {extra[:4]}")
        raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{capture_id} witness rows carry another field, value, comparator "
                                                  f"or state than the re-derived version")

    @staticmethod
    def _compare_disposition(key: str, stored: dict[str, Any], expected: dict[str, Any],
                             authorities: dict[str, tuple[str, ...]] | None = None) -> None:
        if set(stored) != set(expected):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{key} disposition fields {sorted(set(stored) ^ set(expected))}")
        differs = [k for k in expected if _cjson(stored[k]) != _cjson(expected[k])]
        for authority, code, label in DISPOSITION_REFUSALS:
            hit = [k for k in differs if k in (authorities or af.DISPOSITION_AUTHORITY)[authority]]
            if hit:
                raise _refuse(code, f"{key} disposition {hit} differ from the record reconstructed from the {label}")
        if differs:
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{key} disposition {differs} differ from its reconstruction")

    # ------------------------------------------------------------------ decisions
    def decide(self, assertion: dict[str, Any], cutoff: _dt.datetime) -> dict[str, Any]:
        cap = self.captures_by_id[assertion["capture_id"]]
        contest_date = self.by_key[assertion["contest_key"]]["contest_date"]
        observed, observed_reason = base.observed_by_cutoff({"clocks": {"retrieval": cap["clocks"]["retrieval"]}},
                                                            cutoff)
        bound = cap["clocks"]["archive_capture"]["latest_utc"]
        qualified = assertion["field_state"] == QUALIFIED and cap["state"] == "QUALIFIED"
        if qualified:
            if _dt.datetime.strptime(bound, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC) <= cutoff:
                published, reason = TRUE, "ARCHIVED_VERSION_CAPTURED_AT_OR_BEFORE_CUTOFF"
            elif base.ROLES[assertion["field"]] == "OUTCOME" and cutoff < base.earliest_event_instant(contest_date):
                published, reason = FALSE, "OUTCOME_CANNOT_EXIST_BEFORE_EVENT_DATE"
            else:
                published, reason = UNKNOWN, "BEFORE_ARCHIVE_UPPER_BOUND_EARLIER_PUBLICATION_NOT_EXCLUDED"
        else:
            published, reason = UNKNOWN, "ARCHIVED_ASSERTION_NOT_QUALIFIED:" + assertion["field_state"]
        reasons = ["NO_SEPARATE_PIT_ADMISSION_AUTHORITY"]
        if published != TRUE:
            reasons.append("PUBLICATION_NOT_ESTABLISHED_AT_CUTOFF")
        return {"content_corroboration": assertion["corroboration"], "time_evidence_class": cap["time_evidence_class"],
                "archive_upper_bound_utc": bound if qualified else None, "observed_by_cutoff": observed,
                "observed_reason": observed_reason, "historically_published_by_cutoff": published,
                "publication_reason": reason, "pit_admission": {"state": "NOT_ADMITTED", "reasons": reasons}}

    def field_archive(self, key: str, field: str, cutoff: _dt.datetime) -> dict[str, Any]:
        disposition = self.by_key.get(key)
        if disposition is None:
            return {"in_archive_tranche": False, "disposition": None, "historically_published_by_cutoff": NO_ARCHIVE,
                    "publication_reason": "CONTEST_OUTSIDE_THE_ARCHIVE_TRANCHE", "qualified_capture_ids": [],
                    "other_capture_ids": [], "earliest_qualified_upper_bound_utc": None}
        mine = [c for c in self.captures if c["contest_key"] == key]
        qualified = [c for c in mine if c["state"] == "QUALIFIED" and c["field_states"][field] == QUALIFIED]
        decisions = []
        for cap in qualified:
            item = next(a for a in self.assertions if a["capture_id"] == cap["capture_id"] and a["field"] == field)
            decisions.append(self.decide(item, cutoff)["historically_published_by_cutoff"])
        if not decisions:
            state, reason = NO_ARCHIVE, "NO_ARCHIVED_VERSION_QUALIFIES_THIS_FIELD"
        elif TRUE in decisions:
            state, reason = TRUE, "ARCHIVED_VERSION_CAPTURED_AT_OR_BEFORE_CUTOFF"
        elif all(d == FALSE for d in decisions):
            state, reason = FALSE, "OUTCOME_CANNOT_EXIST_BEFORE_EVENT_DATE"
        else:
            state, reason = UNKNOWN, "BEFORE_ARCHIVE_UPPER_BOUND_EARLIER_PUBLICATION_NOT_EXCLUDED"
        bounds = sorted(c["clocks"]["archive_capture"]["latest_utc"] for c in qualified)
        return {"in_archive_tranche": True, "disposition": disposition["disposition"],
                "historically_published_by_cutoff": state, "publication_reason": reason,
                "qualified_capture_ids": [c["capture_id"] for c in qualified],
                "other_capture_ids": [c["capture_id"] for c in mine if c not in qualified],
                "earliest_qualified_upper_bound_utc": bounds[0] if bounds else None}

    @staticmethod
    def compose(original: str, archive: str) -> str:
        if TRUE in (original, archive):
            return TRUE
        if original == FALSE and archive in (FALSE, NO_ARCHIVE):
            return FALSE
        if original == "NO_CORROBORATING_ASSERTION" and archive == FALSE:
            return FALSE
        if original == "NO_CORROBORATING_ASSERTION" and archive == NO_ARCHIVE:
            return "NO_CORROBORATING_ASSERTION"
        return UNKNOWN

    # ------------------------------------------------------------------ query
    def binding_block(self) -> dict[str, Any]:
        block = {"archive_identity": self.binding["archive_identity"],
                 "archive_content_identity": self.binding["content_identity"],
                 "archive_contract_id": self.meta["contract_id"], "archive_contract_sha256": self.binding["contract_sha256"],
                 "acquisition_identity": self.meta["acquisition_identity"],
                 "tranche_sha256": self.meta["tranche_sha256"], "tranche_keys": len(self.dispositions),
                 "parent_source_time_identity": self.source.binding["database_identity"],
                 "verification": VERIFICATION, **self.row_labels}
        if self.expansion:
            block.update(cohort_sha256=self.meta["cohort_sha256"],
                         retained_acquisition_identity=self.authority.retained_acquisition_identity,
                         union_keys=len(self.dispositions))
        return block

    def query(self, grain: str, **kwargs: Any) -> dict[str, Any]:
        if grain in ARCHIVE_GRAINS:
            return self._archive_grain(grain, **kwargs)
        result = self.source.query(grain, **kwargs)
        if grain in ("contest", "contribution"):
            when = base.parse_cutoff(kwargs.get("cutoff"))
            for row in result["rows"]:
                if grain == "contest":
                    key = row["contest"]["contest_key"]
                    row["archive_disposition"] = (self.by_key.get(key) or {}).get("disposition") or \
                        "NOT_IN_ARCHIVE_TRANCHE"
                    for field, value in row["fields"].items():
                        value["archive"] = self.field_archive(key, field, when)
                        value["historically_published_by_cutoff_with_archive"] = self.compose(
                            value["historically_published_by_cutoff"], value["archive"]["historically_published_by_cutoff"])
                else:
                    key = row["relation"]["contributor_contest_key"]
                    for field, value in row["required_field_decisions"].items():
                        archive = self.field_archive(key, field, when)
                        value["archive_published_by_cutoff"] = archive["historically_published_by_cutoff"]
                        value["published_by_cutoff_with_archive"] = self.compose(
                            value["historically_published_by_cutoff"], archive["historically_published_by_cutoff"])
                    row["inputs_published_by_cutoff_with_archive"] = base.aggregate_all(
                        [v["published_by_cutoff_with_archive"] for v in row["required_field_decisions"].values()])
        result["archive_evidence"] = self.binding_block()
        return result

    def _archive_grain(self, grain: str, *, cutoff: str | None = None, season: int | None = None,
                       team: str | None = None, contest: str | None = None, field: str | None = None,
                       evidence_class: str | None = None, source_kind: str | None = None,
                       relation_type: str | None = None, join_state: str | None = None, limit: int | None = 50,
                       offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        if offset < 0:
            raise base.SourceTimeQueryError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise base.SourceTimeQueryError("NEGATIVE_LIMIT", "limit must be zero or positive")
        if evidence_class is not None or source_kind is not None or relation_type is not None or join_state is not None \
                or (field is not None and grain != "archive-assertion"):
            raise base.SourceTimeQueryError("FILTER_NOT_APPLICABLE", f"filter does not apply to the {grain} grain")
        filters: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise base.SourceTimeQueryError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if team is not None:
            filters["team"] = base.normalize_team(team)
        if contest is not None:
            filters["contest"] = base.normalize_contest(contest)
        if field is not None:
            filters["field"] = base._choice(field, FIELDS, "FIELD_INVALID")
        when = base.parse_cutoff(cutoff) if grain == "archive-assertion" else (
            base.parse_cutoff(cutoff) if cutoff else None)
        keys = [d["contest_key"] for d in self.dispositions
                if filters.get("season") in (None, d["season"]) and filters.get("contest") in (None, d["contest_key"])
                and filters.get("team") in (None, d["a_key"], d["b_key"])]
        if grain == "archive-disposition":
            items: list[Any] = [self.by_key[k] for k in keys]
        elif grain == "archive-request":
            items = [r for r in self.requests if r["contest_key"] in keys]
        elif grain == "archive-capture":
            items = [c for k in keys for c in self.captures if c["contest_key"] == k]
        else:
            items = [{"assertion": a, "decision": None} for k in keys for a in self.assertions
                     if a["contest_key"] == k and filters.get("field") in (None, a["field"])]
        total = len(items)
        stop = None if all_rows else offset + (limit or 0)
        rows = items[offset:stop]
        if grain == "archive-assertion":
            rows = [{"assertion": r["assertion"], "decision": self.decide(r["assertion"], when)} for r in rows]
        return {"grain": grain, "filters": filters,
                "cutoff": None if when is None else {"literal": cutoff, "utc": base._fmt(when)},
                "offset": offset, "limit": None if all_rows else limit, "total": total, "returned": len(rows),
                "rows": rows, "next_offset": offset + len(rows) if offset + len(rows) < total else None,
                "archive_evidence": self.binding_block(), **self.row_labels}
