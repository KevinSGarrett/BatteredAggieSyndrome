r"""Read-only archive-supported 2019 prior-game history availability query (BAT-714, Cycle #42 TP42-A01).

``bas-history-availability-query --database <canonical\national_history_availability_2019\sha256\<id>\
national_history_availability.sqlite> --cutoff 2019-09-06T10:00:00Z --grain history --contest ncaa:1735310``

Standard library only (plus the shared core and the accepted parent readers). Before any row is served:

* the projection database must sit at ``<root>/sha256/<id>/national_history_availability.sqlite`` with its run
  manifest at ``<data>/manifests/<population>/sha256/<id>/run_manifest.json``; ``<id>`` must equal the SHA-256 of the
  manifest's database identity document, which names the database bytes, content identity, parent and table counts;
  meta, labels and counts must agree; ``--expect-identity`` that differs refuses;
* the projection must name the issued contract and its exact parents (PROJECTION_CONTRACT_NOT_ISSUED /
  PARENT_NOT_ISSUED); every parent -- population, history, source-time and the V1.2 archive sidecar (re-derived from
  its raw bytes and receipts by the accepted ``ArchiveEvidence`` reader) -- is verified at its recorded identity;
* the whole projection is re-derived from the verified parents and every stored record compared; any coordinated
  change, even with every outer hash recomputed, refuses with the first semantic class it reaches;
* the content identity it displays is never a claim copied from the database: the defined content identity document
  (contract identity_scheme: issued contract, verified parents, payload schema and encoding, the semantic and stored
  gzip-mtime-0 hashes and row counts of the re-derived, verified payloads) is recomputed and must hash to the identity
  that the meta and the manifest both claim (CONTENT_IDENTITY_MISSING / CONTENT_IDENTITY_MISMATCH), and the meta's
  restated payload schema, payload hashes and row counts must equal that document (CONTENT_DECLARATION_MISMATCH).

Grains ``target`` (769 targets), ``history`` (two views per target), ``relationship`` (every expected strictly earlier
same-season prior relationship) and ``prior-evidence`` (the archived versions and field witnesses of each referenced
prior contest) are served at an explicit, timezone-aware ``--cutoff`` with exact totals and paging. A prior result is
supported only by one archived version qualifying all six fields with an upper bound at or before the cutoff;
supported-subset totals and exact unreduced rates are reported beside the complete expected denominator and every
unsupported reason class. Nothing is PIT admitted; ``--require-pit`` refuses; seasons other than 2019 are
NOT_YET_AUDITED.
"""
from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterator, Sequence

from aggie_analytics.national_history import availability as core

GRAINS = ("target", "history", "relationship", "prior-evidence")
APPLICABLE = {"target": {"season", "contest", "team"},
              "history": {"season", "contest", "team", "view"},
              "relationship": {"season", "contest", "team", "view", "support_state"},
              "prior-evidence": {"season", "contest", "team"}}
IDENTITY_RE = re.compile(r"^[0-9a-f]{64}$")
TEAM_RE = re.compile(r"^(?:org:)?([0-9]{1,12})$")
CONTEST_RE = re.compile(r"^(?:ncaa|nolink|cfbd):[^\x00-\x1f]{1,200}$")
OUT_OF_SCOPE_STATE = "NOT_YET_AUDITED"
IN_SCOPE_STATE = "AUDITED_2019_TARGET_POPULATION"
VERIFICATION = "PROJECTION_IDENTITY_PARENTS_AND_FULL_REDERIVATION_VERIFIED"
EXTENDED_PREFIX = "\\\\?\\"
Error = core.AvailabilityError


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def readonly_uri(database: Path) -> str:
    """A read-only ``file:`` URI naming the database as given (made absolute, not resolved): on Windows
    ``Path.resolve()`` returns an extended-length (EXTENDED_PREFIX) path for a long location, whose URI SQLite
    rejects."""
    text = os.path.abspath(os.fspath(database))
    if text.startswith(EXTENDED_PREFIX):
        text = text[len(EXTENDED_PREFIX):]
    return Path(text).as_uri() + "?mode=ro"


def manifest_path_for(database: Path) -> Path:
    db = Path(database).resolve()
    population_root = db.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / db.parent.name / \
        "run_manifest.json"


def normalize_team(value: str) -> str:
    match = TEAM_RE.match(str(value).strip())
    if not match:
        raise Error("TEAM_KEY_INVALID", f"team must be an organization key org:<digits>, got {value!r}")
    return f"org:{int(match.group(1))}"


def normalize_contest(value: str) -> str:
    text = str(value)
    if text.isdigit() and len(text) <= 12:
        return f"ncaa:{text}"
    if not CONTEST_RE.match(text):
        raise Error("CONTEST_KEY_INVALID", f"contest must be a parent contest key, got {value!r}")
    return text


# --------------------------------------------------------------------------------------------- issued authority

_REGISTERED: list[dict[str, Any]] = []


@contextlib.contextmanager
def registered_authority(authority: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """In-process development and test hook: accept one further issued authority ({contract_id, contract_sha256,
    parent}) for the duration of the block. The console and module entry points never register anything; they serve
    only the packaged issued authority (``core.ISSUED``)."""
    _REGISTERED.append(authority)
    try:
        yield authority
    finally:
        _REGISTERED.remove(authority)


def issued_authority(contract_sha256: Any, parent: Any) -> dict[str, Any]:
    candidates = [a for a in [core.ISSUED, *_REGISTERED] if a["contract_sha256"] == contract_sha256]
    if not candidates:
        raise Error("PROJECTION_CONTRACT_NOT_ISSUED", f"contract sha256 {contract_sha256!r} is not an issued contract "
                                                      "this consumer serves")
    for authority in reversed(candidates):
        if authority["parent"] == parent:
            return authority
    raise Error("PARENT_NOT_ISSUED", "the projection names parents other than the issued contract's exact parents")


# --------------------------------------------------------------------------------------------- verification

def gzip_mtime0(data: bytes) -> bytes:
    """The defined stored-payload encoding (``core.PAYLOAD_ENCODING``): gzip, mtime 0, no file name, level 9."""
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as stream:
        stream.write(data)
    return buffer.getvalue()


def content_document(contract_id: str, contract_sha256: str, parent: dict[str, Any],
                     payloads: dict[str, bytes]) -> dict[str, Any]:
    """The defined content identity document (contract identity_scheme.content_identity) of verified payload bytes."""
    return {"schema": core.CONTENT_SCHEMA, "stage": "history-availability-content", "population": core.POPULATION,
            "contract_id": contract_id, "contract_sha256": contract_sha256, "parent": parent,
            "payload_schema": core.PAYLOAD_SCHEMA, "payload_encoding": core.PAYLOAD_ENCODING,
            "semantic_outputs": {name: core.sha256_bytes(payloads[name]) for name in core.PAYLOAD_FILES},
            "outputs": {f"{name}.gz": core.sha256_bytes(gzip_mtime0(payloads[name])) for name in core.PAYLOAD_FILES},
            "row_counts": {name: payloads[name].count(b"\n") for name in core.PAYLOAD_FILES}}


def _meta_json(value: Any) -> Any:
    """A JSON meta value, or the raw value when it is not JSON (so it can never equal a defined document field)."""
    try:
        return json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return value


def verify_database(database: Path, *, expect_identity: str | None = None) -> dict[str, Any]:
    db = Path(database)
    if not db.is_file():
        raise Error("DATABASE_MISSING", f"no database file at {db}")
    if db.name != core.DB_FILE or db.resolve().parent.parent.name != "sha256":
        raise Error("DATABASE_LOCATION_INVALID", "the database must sit at <root>/sha256/<id>/" + core.DB_FILE)
    identity = db.resolve().parent.name
    if not IDENTITY_RE.match(identity):
        raise Error("DATABASE_LOCATION_INVALID", f"directory name {identity!r} is not a SHA-256 identity")
    manifest_path = manifest_path_for(db)
    if not manifest_path.is_file():
        raise Error("MANIFEST_MISSING", f"no run manifest at {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity_document = document["identity_document"]
        computed = core.sha256_bytes(core.canonical_json_bytes(identity_document))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Error("MANIFEST_MALFORMED", str(exc)) from exc
    if computed != identity or document.get("identity") != identity:
        raise Error("DATABASE_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                  f"{identity}")
    if (identity_document.get("stage"), identity_document.get("schema"), identity_document.get("db_schema_version"),
            identity_document.get("population")) != ("history-availability-database", core.DATABASE_SCHEMA,
                                                     core.DB_SCHEMA, core.POPULATION):
        raise Error("DATABASE_SCHEMA_UNSUPPORTED", "the manifest is not a known history-availability database manifest")
    expected = (identity_document.get("outputs") or {}).get(core.DB_FILE)
    actual = _sha256_file(db)
    if expected != actual:
        raise Error("DATABASE_TAMPERED", f"database bytes hash to {actual}, manifest names {expected}")
    if expect_identity is not None and expect_identity != identity:
        raise Error("STALE_DATABASE_IDENTITY", f"expected {expect_identity}, found {identity}")
    return {"database_identity": identity, "database_sha256": actual, "manifest": str(manifest_path),
            "content_identity": identity_document.get("content_identity"),
            "contract_sha256": identity_document.get("contract_sha256"), "parent": identity_document.get("parent"),
            "table_counts": identity_document.get("table_counts")}


def default_parent_paths(database: Path, parent: dict[str, Any]) -> dict[str, Path]:
    """``<data>/canonical/<parent population>/sha256/<recorded identity>/<file>`` beside the projection's own root."""
    canonical = Path(database).resolve().parents[3]
    out = {}
    for name, (population, filename) in core.PARENT_FILES.items():
        ident = (parent.get(name) or {}).get("query_db_identity" if name == "population" else "database_identity")
        if not isinstance(ident, str) or not IDENTITY_RE.match(ident):
            raise Error("PARENT_NOT_ISSUED", f"{name} parent identity {ident!r}")
        out[name] = canonical / population / "sha256" / ident / filename
    return out


class HistoryAvailabilityDatabase:
    """A verified, read-only, fully re-derived handle on one history-availability projection."""

    def __init__(self, database: Path, *, expect_identity: str | None = None,
                 parent_paths: dict[str, Path | None] | None = None) -> None:
        self.binding = verify_database(database, expect_identity=expect_identity)
        conn = sqlite3.connect(readonly_uri(database), uri=True)
        try:
            meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
            counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in core.TABLES}
            stored = {name: [row[0].encode("utf-8") + b"\n" for row in conn.execute(
                f"SELECT record FROM {table} ORDER BY ord")] for name, table in core.PAYLOAD_TABLES.items()}
        except sqlite3.DatabaseError as exc:
            raise Error("DATABASE_SCHEMA_UNSUPPORTED", str(exc)) from exc
        finally:
            conn.close()
        if meta.get("schema_version") != core.DB_SCHEMA:
            raise Error("DATABASE_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        try:
            labels = json.loads(meta.get("row_labels") or "null")
            parent = json.loads(meta.get("parent") or "null")
        except ValueError as exc:
            raise Error("DATABASE_SCHEMA_UNSUPPORTED", f"meta is not JSON: {exc}") from exc
        if labels != core.ROW_LABELS:
            raise Error("FORGED_AUTHORITY_LABEL", "meta row labels differ from the evidence-only labels")
        claims = {"manifest": self.binding["content_identity"], "meta": meta.get("content_identity")}
        absent = sorted(k for k, v in claims.items() if not isinstance(v, str) or not v)
        if absent:
            raise Error("CONTENT_IDENTITY_MISSING", f"no content identity claim in the {' and '.join(absent)}")
        if meta.get("content_identity") != self.binding["content_identity"] or \
                meta.get("contract_sha256") != self.binding["contract_sha256"] or parent != self.binding["parent"]:
            raise Error("DATABASE_IDENTITY_MISMATCH", "database meta and manifest identities differ")
        if counts != self.binding["table_counts"]:
            raise Error("DATABASE_COUNT_MISMATCH", f"table counts {counts} differ from the manifest")
        if (meta.get("season"), meta.get("prior_rule"), meta.get("support_rule"), meta.get("cross_version_rule")) != (
                str(core.SEASON), core.PRIOR_RULE, core.SUPPORT_RULE, core.CROSS_VERSION_RULE):
            raise Error("FORGED_AUTHORITY_LABEL", "meta season, prior, support or cross-version rule differs")
        authority = issued_authority(meta.get("contract_sha256"), parent)
        if meta.get("contract_id") != authority["contract_id"]:
            raise Error("PROJECTION_CONTRACT_NOT_ISSUED", f"contract id {meta.get('contract_id')!r}")
        paths = default_parent_paths(database, parent)
        for name, path in (parent_paths or {}).items():
            if path is not None:
                paths[name] = Path(path)
        opened = core.open_parents(paths, parent)
        if opened["parent"] != parent:
            raise Error("PARENT_BINDING_MISMATCH", "verified parents differ from the recorded parents")
        projection = core.Projection(opened["population_rows"], opened["subset"], opened["history_targets"],
                                     opened["history_views"], opened["archive"])
        derived = projection.payloads()
        for name in core.PAYLOAD_FILES:
            problem = core.mismatch(name, derived[name].splitlines(keepends=True), stored[name])
            if problem is not None:
                raise Error(*problem)
        # The displayed content identity is the identity of the defined content document of the verified payloads;
        # the database and manifest claims (outer hashes recomputable by anyone) must equal it, never replace it.
        document = content_document(authority["contract_id"], authority["contract_sha256"], opened["parent"], derived)
        content_identity = core.sha256_bytes(core.canonical_json_bytes(document))
        if self.binding["content_identity"] != content_identity:
            raise Error("CONTENT_IDENTITY_MISMATCH", f"the database and manifest claim content identity "
                                                     f"{self.binding['content_identity']}; its verified payloads "
                                                     f"define {content_identity}")
        declared = {"payload_schema": meta.get("payload_schema"),
                    "payload_sha256": _meta_json(meta.get("payload_sha256")),
                    "row_counts": _meta_json(meta.get("row_counts"))}
        defined = {"payload_schema": document["payload_schema"], "payload_sha256": document["semantic_outputs"],
                   "row_counts": document["row_counts"]}
        differing = sorted(k for k in defined if declared[k] != defined[k])
        if differing:
            raise Error("CONTENT_DECLARATION_MISMATCH", f"meta {differing} differ from the content document of the "
                                                        "verified payloads")
        self.content_identity = content_identity
        self.content_document = document
        self.meta = meta
        self.parent = parent
        self.paths = {k: str(v) for k, v in paths.items()}
        self.targets = [json.loads(line) for line in stored["targets.jsonl"]]
        self.views = [json.loads(line) for line in stored["views.jsonl"]]
        self.relationships = [json.loads(line) for line in stored["relationships.jsonl"]]
        self.evidence = {r["contest_key"]: r for r in (json.loads(line) for line in stored["evidence.jsonl"])}
        self.evidence_order = [json.loads(line)["contest_key"] for line in stored["evidence.jsonl"]]
        self.witnesses: dict[str, list[dict[str, Any]]] = {}
        for line in stored["witnesses.jsonl"]:
            row = json.loads(line)
            self.witnesses.setdefault(row["contest_key"], []).append(row)
        self.by_view: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for rel in self.relationships:
            self.by_view.setdefault((rel["target_contest_key"], rel["view"]), []).append(rel)
        self.view_team = {(v["target_contest_key"], v["view"]): v["team_key"] for v in self.views}

    def close(self) -> None:
        return None

    def __enter__(self) -> "HistoryAvailabilityDatabase":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ query
    def binding_block(self) -> dict[str, Any]:
        return {"database_identity": self.binding["database_identity"],
                "content_identity": self.content_identity, "contract_id": self.meta["contract_id"],
                "contract_sha256": self.meta["contract_sha256"], "parent": self.parent,
                "verification": VERIFICATION, "support_rule": core.SUPPORT_RULE,
                "cross_version_rule": core.CROSS_VERSION_RULE, "prior_rule": core.PRIOR_RULE}

    def _team(self, target_key: str, view: str, cutoff: Any) -> dict[str, Any]:
        return core.summarize(self.view_team[(target_key, view)], self.by_view.get((target_key, view), []),
                              self.evidence, cutoff)

    def _relationship_row(self, rel: dict[str, Any], cutoff: Any) -> dict[str, Any]:
        evidence = self.evidence[rel["prior_contest_key"]]
        decision = core.decide(rel, evidence, cutoff)
        witnesses = self.witnesses.get(rel["prior_contest_key"], [])
        decision["supporting_versions"] = [
            {"capture_id": cid, "upper_bound_utc": next(v["upper_bound_utc"] for v in evidence["archive"]["versions"]
                                                        if v["capture_id"] == cid),
             "witnesses": [{"field": w["field"], "witness": w["witness"], "witness_span": w["witness_span"],
                            "literal": w["literal"]} for w in witnesses if w["capture_id"] == cid]}
            for cid in decision["supporting_capture_ids"]]
        archive = evidence["archive"]
        return {"relationship": rel, "evidence": {
            "evidence_class": archive["evidence_class"], "evidence_reason": archive["evidence_reason"],
            "in_tranche": archive["in_tranche"], "archive_disposition": archive["archive_disposition"],
            "coherent_capture_ids": archive["coherent_capture_ids"],
            "coherent_upper_bound_utc": archive["coherent_upper_bound_utc"],
            "field_earliest_qualified_upper_bound_utc": archive["field_earliest_qualified_upper_bound_utc"],
            "versions": [{"capture_id": v["capture_id"], "state": v["state"], "upper_bound_utc": v["upper_bound_utc"]}
                         for v in archive["versions"]],
            "parent_values": evidence["parent_values"],
            "earliest_event_instant_utc": evidence["earliest_event_instant_utc"]},
            "decision": decision, "cutoff_position": core.cutoff_position(rel["target_date"], cutoff)}

    def query(self, grain: str, *, cutoff: str | None, season: int | None = None, team: str | None = None,
              contest: str | None = None, view: str | None = None, support_state: str | None = None,
              limit: int | None = 50, offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        if grain not in GRAINS:
            raise Error("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        when = core.parse_cutoff(cutoff)
        if offset < 0:
            raise Error("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise Error("NEGATIVE_LIMIT", "limit must be zero or positive")
        given = {"season": season, "team": team, "contest": contest, "view": view, "support_state": support_state}
        for name, value in given.items():
            if value is not None and name not in APPLICABLE[grain]:
                raise Error("FILTER_NOT_APPLICABLE", f"--{name.replace('_', '-')} does not apply to the {grain} grain")
        filters: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise Error("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if team is not None:
            filters["team"] = normalize_team(team)
        if contest is not None:
            filters["contest"] = normalize_contest(contest)
        if view is not None:
            if view not in ("A", "B"):
                raise Error("VIEW_INVALID", f"view must be A or B, got {view!r}")
            filters["view"] = view
        if support_state is not None:
            if support_state not in core.SUPPORT_STATES:
                raise Error("SUPPORT_STATE_INVALID", f"support state must be one of {list(core.SUPPORT_STATES)}")
            filters["support_state"] = support_state
        result: dict[str, Any] = {"grain": grain, "filters": filters,
                                  "cutoff": {"literal": cutoff, "utc": core.fmt(when)},
                                  "offset": offset, "limit": None if all_rows else limit,
                                  "binding": self.binding_block(), **core.ROW_LABELS,
                                  "pit_admission_state": "NOT_ADMITTED", "pregame_claim": False}
        if season is not None and season != core.SEASON:
            result.update(season_scope_state=OUT_OF_SCOPE_STATE, total=None, returned=0, rows=[], next_offset=None,
                          note="season not yet audited by this projection; no rows or totals are fabricated and this "
                               "is not an empty national population")
            return result
        items = self._items(grain, filters, when)
        total = len(items)
        page = items[offset:] if all_rows else items[offset:offset + (limit or 0)]
        rows = [self._render(grain, item, when) for item in page]
        result.update(season_scope_state=IN_SCOPE_STATE, total=total, returned=len(rows), rows=rows,
                      next_offset=offset + len(rows) if offset + len(rows) < total else None)
        return result

    def _items(self, grain: str, filters: dict[str, Any], when: Any) -> list[Any]:
        contest, team, view = filters.get("contest"), filters.get("team"), filters.get("view")
        if grain == "target":
            return [t for t in self.targets if contest in (None, t["contest_key"]) and team in (None, t["a_key"],
                                                                                               t["b_key"])]
        if grain == "history":
            return [v for v in self.views if contest in (None, v["target_contest_key"]) and
                    team in (None, v["team_key"]) and view in (None, v["view"])]
        if grain == "relationship":
            items = [r for r in self.relationships if contest in (None, r["target_contest_key"]) and
                     team in (None, r["team_key"]) and view in (None, r["view"])]
            state = filters.get("support_state")
            if state is not None:
                items = [r for r in items if core.decide(r, self.evidence[r["prior_contest_key"]],
                                                         when)["support_state"] == state]
            return items
        return [self.evidence[k] for k in self.evidence_order if contest in (None, k) and
                team in (None, self.evidence[k]["a_key"], self.evidence[k]["b_key"])]

    def _render(self, grain: str, item: dict[str, Any], when: Any) -> dict[str, Any]:
        if grain == "target":
            key = item["contest_key"]
            return {"target": item, "cutoff_position": core.cutoff_position(item["contest_date"], when),
                    "histories": {"A": self._team(key, "A", when), "B": self._team(key, "B", when)}}
        if grain == "history":
            key, view = item["target_contest_key"], item["view"]
            other = "B" if view == "A" else "A"
            return {"view": item, "cutoff_position": core.cutoff_position(item["target_date"], when),
                    "team_history": self._team(key, view, when), "opponent_history": self._team(key, other, when)}
        if grain == "relationship":
            return self._relationship_row(item, when)
        archive = item["archive"]
        supporting = [v["capture_id"] for v in archive["versions"] if v["capture_id"] in archive["coherent_capture_ids"]
                      and core.parse_bound(v["upper_bound_utc"]) <= when]
        return {"prior_evidence": item, "witnesses": self.witnesses.get(item["contest_key"], []),
                "coherent_version_at_or_before_cutoff": supporting}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bas-history-availability-query", allow_abbrev=False,
                                     description="Read-only archive-supported 2019 prior-game history availability at "
                                                 "an explicit cutoff (evidence only; NOT_ADMITTED).")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--grain", required=True, choices=GRAINS)
    parser.add_argument("--cutoff", default=None, help="ISO-8601 instant with seconds and an explicit zone")
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--team", default=None, help="organization key org:<digits> or bare digits")
    parser.add_argument("--contest", default=None, help="target contest key (prior contest for prior-evidence)")
    parser.add_argument("--view", default=None, help="A or B")
    parser.add_argument("--support-state", default=None)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--expect-identity", default=None)
    parser.add_argument("--population-database", type=Path, default=None)
    parser.add_argument("--history-database", type=Path, default=None)
    parser.add_argument("--source-time-database", type=Path, default=None)
    parser.add_argument("--archive-database", type=Path, default=None)
    parser.add_argument("--require-pit", action="store_true",
                        help="refused: nothing here is PIT admitted (evidence projection only)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.require_pit:
            raise Error("PIT_ADMISSION_NOT_ESTABLISHED", "every row is NOT_ADMITTED archive-supported history "
                                                         "evidence; no PIT or model admission authority exists")
        core.parse_cutoff(args.cutoff)
        paths = {"population": args.population_database, "history": args.history_database,
                 "source_time": args.source_time_database, "archive": args.archive_database}
        with HistoryAvailabilityDatabase(args.database, expect_identity=args.expect_identity,
                                         parent_paths=paths) as db:
            result = db.query(args.grain, cutoff=args.cutoff, season=args.season, team=args.team,
                              contest=args.contest, view=args.view, support_state=args.support_state,
                              limit=args.limit, offset=args.offset, all_rows=args.all_rows)
    except core.AvailabilityError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    # ``python -m`` runs this file as __main__; delegate to the package module so every exception class has one
    # identity (the C41 module-front lesson).
    from aggie_analytics.national_history import availability_query as _front

    raise SystemExit(_front.main())
