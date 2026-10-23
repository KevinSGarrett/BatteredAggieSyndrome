r"""Build machinery of the national recruiting evidence release 2010-2017 (BAT-735, Cycle #64 TP64-A01): the contract
generator's source census, pinned input loading, the per-observation source/person/program/value/time qualification,
the partition, source, summary and census records and the create-only, content-addressed materialization.

``python -B tools/cycle64/build_national_recruiting_evidence.py
--contract configs/national_recruiting_evidence_2010_2017_contract.json --data-root <data>
--output-root <data>/canonical/national_recruiting_evidence_2010_2017
--manifest-root <data>/manifests/national_recruiting_evidence_2010_2017``

Every input is a whole file pinned by SHA-256 and byte count in the committed contract, at a relative locator under the
explicitly named data root (or, for the three repository witnesses, under the checkout); the data root and every
resolved location pass the BAT-717 literal local-file policy before any filesystem access, and nothing is ever written
there. The original acquisition manifest is the request-cell authority: every captured cell's receipt must equal its
manifest entry, every raw array its receipt's bytes, SHA-256 and row count. The eight recruiting arrays are decoded with
their JSON kinds intact (NaN, Infinity, out-of-range floats and over-long integers are refused, never nulls) and every
row is checked against the frozen source schema. The people and core registries are streamed once each for the exact
witnesses of these observations only (identity key, source-mapping entity key, legacy observation id, exact program
label and the referenced team entity); no roster, game, feature or 2024/2025 row is selected.

The builder refuses unless the contract's rules equal :func:`recruiting.rules_document` and every input verifies. It
qualifies every observation (no fit), derives every grain, refuses a derivation whose key universe differs from the
contract's pinned universe (population drift, never forced), writes the deterministic SQLite database and materializes it
create-only: an existing identity is verified, never rewritten, and differing bytes at an existing identity are refused.
The materialized database is then opened through the reader's complete verification with the contract's anchors.
``--input-order`` (natural, reverse, shuffle:<seed>), ``--chunk-size`` with ``--checkpoint-dir`` and
``--stop-after-chunks``/``--resume`` prove that processing order, chunking and an interrupted build cannot change a byte;
every observation keeps its zero-based original raw-array ordinal. No source request, activation, admission or default
change is made.

Adapted from the accepted Cycle 63 builder (its checkpoint, order, materialization and receipt machinery).
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import json
import os
import platform
import random
import sqlite3
import sys
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any, Callable, Sequence

from aggie_analytics import readonly_sqlite
from aggie_analytics.personnel_evidence import recruiting as rc

PRODUCER = "national_recruiting_evidence_2010_2017/1.0.0"
CHECKPOINT_SCHEMA = "BAS-RECRUITING-EVIDENCE-CHECKPOINT-1"
CONTRACT_SCHEMA = "BAS-RECRUITING-EVIDENCE-CONTRACT-1"
INTERRUPTED_EXIT = 3
ANCHOR_KEYS = ("inputs", "expected", "frozen_at_utc")
ACQUISITION_REL = "manifests/acquisition/bat388-people-sources-v1/people_source_acquisition_manifest.json"
PEOPLE_MANIFEST_REL = "artifacts/entities/canonical_people_registry_manifest.json"
CORE_MANIFEST_REL = "artifacts/entities/canonical_core_registry_manifest.json"
RIGHTS_REL = "artifacts/source_governance/tier1_rights_decisions.csv"
LEGACY_BUILDER_REL = "runtime/BAT-388/build_canonical_people_registry.py"
RIGHTS_DECISION_ID = "PRIVATE-RESEARCH-SRC-002"
RIGHTS_FIELDS = ("decision_id", "source_id", "provider", "dataset", "owner_authorization_basis", "policy_version",
                 "allowed_access", "local_storage_decision", "derived_use_decision", "publication_decision",
                 "redistribution_decision", "retention_decision", "attribution_decision", "rights_decision",
                 "rights_metadata_nonblocking", "private_research_acquisition_allowed")
#: The capture receipt members the contract pins for every captured cell.
CAPTURE_FIELDS = ("capture_id", "dataset", "parameters", "endpoint_id", "source_uri", "http_status", "result",
                  "capture_known_at_utc", "retrieved_at_utc", "response_sha256", "response_bytes", "row_count",
                  "immutable_path", "historical_coverage_status", "upstream_lineage", "top_level_schema_fields",
                  "run_id", "source_id")
CAPTURED_DATASETS = (rc.RECRUIT_DATASET, rc.PORTAL_DATASET)


class BuildRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise rc.RecruitingError(code, message)


_io_path = rc._io_path
sha256_file = rc.sha256_file
sha256_bytes = rc.sha256_bytes


# --------------------------------------------------------------------------------------------- locations and files

def _literal(path: Path, code_prefix: str) -> str:
    try:
        return readonly_sqlite.literal_path(path)
    except readonly_sqlite.DatabaseLocationError as exc:
        suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
        raise rc.RecruitingError(f"{code_prefix}_LOCATION_{suffix}", exc.detail) from exc


def _root(path: Path) -> Path:
    root = Path(_literal(Path(path), "RECRUITING_DATA_ROOT"))
    if not _io_path(root).is_dir():
        _refuse("RECRUITING_DATA_ROOT_MISSING", f"no root directory at {path}")
    return root


def _located(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or relative.startswith(("/", "\\")) or ".." in relative.split("/") \
            or ":" in relative or "\\" in relative:
        _refuse("RECRUITING_INPUT_LOCATION_UNSUPPORTED", f"{relative!r} is not a relative forward-slash locator")
    return Path(_literal(root / Path(*relative.split("/")), "RECRUITING_INPUT"))


def _file_bytes(path: Path, name: str) -> bytes:
    if not _io_path(path).is_file():
        _refuse("RECRUITING_INPUT_MISSING", f"{name}: no file at {path}")
    try:
        return _io_path(path).read_bytes()
    except OSError as exc:
        raise rc.RecruitingError("RECRUITING_INPUT_MALFORMED", f"{name}: {exc}") from exc


def _json_bytes(data: bytes, name: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise rc.RecruitingError("RECRUITING_INPUT_MALFORMED", f"{name}: not UTF-8 ({exc})") from exc
    if text.startswith(chr(0xFEFF)):
        _refuse("RECRUITING_INPUT_MALFORMED", f"{name}: a byte-order mark precedes the JSON")
    return rc.loads_untrusted(text, "RECRUITING_INPUT_MALFORMED", name)


def _spec(locator: str, relative: str, data: bytes, **extra: Any) -> dict[str, Any]:
    return {"locator": locator, "relative_path": relative, "sha256": sha256_bytes(data), "bytes": len(data), **extra}


# --------------------------------------------------------------------------------------------- source census

def _capture_spec(receipt: dict[str, Any], receipt_rel: str, receipt_bytes: bytes) -> dict[str, Any]:
    missing = [f for f in CAPTURE_FIELDS if f not in receipt]
    headers = receipt.get("response_headers")
    if missing or not isinstance(headers, dict) or not isinstance(headers.get("date"), str):
        _refuse("RECRUITING_RECEIPT_MISMATCH", f"capture receipt {receipt_rel} lacks {missing or ['response date']}")
    spec = {f: receipt[f] for f in CAPTURE_FIELDS}
    params = spec["parameters"]
    if not isinstance(params, dict) or not params or not all(isinstance(k, str) and rc.is_int(v)
                                                              for k, v in params.items()):
        _refuse("RECRUITING_RECEIPT_MISMATCH", f"capture receipt {receipt_rel}: parameters are not integer-valued")
    if not (isinstance(spec["capture_id"], str) and rc.CAPTURE_ID_RE.match(spec["capture_id"])) or \
            not rc.is_int(spec["row_count"]) or not rc.is_int(spec["response_bytes"]) or \
            not (isinstance(spec["response_sha256"], str) and rc.SHA_RE.match(spec["response_sha256"])) or \
            not all(isinstance(spec[k], str) and rc.UTC_SECOND_RE.match(spec[k])
                    for k in ("capture_known_at_utc", "retrieved_at_utc")):
        _refuse("RECRUITING_RECEIPT_MISMATCH", f"capture receipt {receipt_rel}: identity, clock or count is malformed")
    spec.update(provider_http_date=headers["date"], receipt_relative_path=receipt_rel,
                receipt_sha256=sha256_bytes(receipt_bytes), receipt_bytes=len(receipt_bytes))
    return spec


def source_census(data_root: Path, repo_root: Path, *, acquisition_rel: str = ACQUISITION_REL,
                  people_manifest_rel: str = PEOPLE_MANIFEST_REL, core_manifest_rel: str = CORE_MANIFEST_REL,
                  rights_rel: str = RIGHTS_REL, legacy_rel: str = LEGACY_BUILDER_REL) -> tuple[dict, dict]:
    """(inputs, expected) of the contract from the original sources: the requested-cell universe of the acquisition
    manifest, every captured cell's receipt (equal to its manifest entry) and raw array (bytes, SHA-256 and row count),
    the observation key universe of every recruiting array (ordinal and source recruit ID only: no person, program,
    value or time decision), the two registries pinned by their manifests and the repository witnesses. Source keys
    only; no qualification."""
    data, repo = _root(data_root), _root(repo_root)
    acquisition_bytes = _file_bytes(_located(data, acquisition_rel), "acquisition_manifest")
    manifest = _json_bytes(acquisition_bytes, "acquisition_manifest")
    if not isinstance(manifest, dict) or manifest.get("source_id") != rc.SOURCE_ID or \
            not isinstance(manifest.get("captures"), list) or not isinstance(manifest.get("missing_requests"), list):
        _refuse("RECRUITING_INPUT_MALFORMED", "the acquisition manifest is not the SRC-002 request ledger")
    inputs: dict[str, Any] = {}
    captures: dict[str, Any] = {}
    cells: list[dict[str, Any]] = []
    observations: dict[str, Any] = {}
    for entry in manifest["captures"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("capture_manifest_path"), str):
            _refuse("RECRUITING_INPUT_MALFORMED", "an acquisition capture entry names no receipt")
        receipt_rel = entry["capture_manifest_path"]
        receipt_bytes = _file_bytes(_located(data, receipt_rel), receipt_rel)
        receipt = _json_bytes(receipt_bytes, receipt_rel)
        if not isinstance(receipt, dict) or \
                rc.canonical_json_bytes({k: v for k, v in entry.items() if k != "capture_manifest_path"}) != \
                rc.canonical_json_bytes(receipt):
            _refuse("RECRUITING_RECEIPT_MISMATCH", f"{receipt_rel} differs from its acquisition manifest entry")
        spec = _capture_spec(receipt, receipt_rel, receipt_bytes)
        if spec["dataset"] not in CAPTURED_DATASETS or set(spec["parameters"]) != {"year"} or \
                spec["source_id"] != rc.SOURCE_ID or spec["result"] != "SUCCESS" or spec["http_status"] != 200:
            _refuse("RECRUITING_INPUT_MALFORMED", f"{receipt_rel}: not a successful single-year recruiting or portal "
                                                  "capture")
        year = spec["parameters"]["year"]
        name = "recruiting_players" if spec["dataset"] == rc.RECRUIT_DATASET else "transfer_portal"
        receipt_name = "recruiting_receipt" if name == "recruiting_players" else "portal_receipt"
        if f"{name}:{year}" in inputs or spec["capture_id"] in captures:
            _refuse("RECRUITING_INPUT_MALFORMED", f"{name} {year} or {spec['capture_id']} is captured twice")
        raw = _file_bytes(_located(data, spec["immutable_path"]), spec["immutable_path"])
        if (sha256_bytes(raw), len(raw)) != (spec["response_sha256"], spec["response_bytes"]):
            _refuse("RECRUITING_INPUT_TAMPERED", f"{spec['immutable_path']}: bytes differ from the receipt's")
        rows = _json_bytes(raw, spec["immutable_path"])
        if not isinstance(rows, list) or len(rows) != spec["row_count"]:
            _refuse("RECRUITING_INPUT_MALFORMED", f"{spec['immutable_path']}: not the receipt's array of "
                                                  f"{spec['row_count']} rows")
        inputs[f"{name}:{year}"] = _spec("DATA_ROOT", spec["immutable_path"], raw, rows=len(rows),
                                         capture_id=spec["capture_id"])
        inputs[f"{receipt_name}:{year}"] = _spec("DATA_ROOT", receipt_rel, receipt_bytes, capture_id=spec["capture_id"])
        captures[spec["capture_id"]] = spec
        cells.append({"cell_key": rc.cell_key(spec["dataset"], spec["parameters"]), "dataset": spec["dataset"],
                      "parameters": spec["parameters"], "state": "CAPTURED", "missing_reason": None,
                      "capture_id": spec["capture_id"]})
        if name == "recruiting_players":
            if year not in rc.RECRUIT_SEASONS:
                _refuse("RECRUITING_INPUT_POPULATION_DRIFT", f"recruiting capture {year} is outside 2010-2017")
            keys = []
            for ordinal, row in enumerate(rows):
                recruit = row.get("id") if isinstance(row, dict) else None
                if not (isinstance(recruit, str) and rc.RECRUIT_ID_RE.match(recruit)):
                    _refuse("RECRUITING_SOURCE_SCHEMA_INVALID", f"{spec['immutable_path']} row {ordinal}: no source "
                                                                "recruit ID of 1-12 ASCII digits")
                keys.append(rc.observation_key(spec["capture_id"], ordinal, recruit))
            observations[str(year)] = {"capture_id": spec["capture_id"], "rows": len(rows),
                                       "keys_sha256": rc.keys_sha256(keys)}
    for request in manifest["missing_requests"]:
        params = request.get("parameters") if isinstance(request, dict) else None
        if not isinstance(params, dict) or not params or not isinstance(request.get("dataset"), str) or \
                not isinstance(request.get("reason"), str) or \
                not all(isinstance(k, str) and rc.is_int(v) for k, v in params.items()):
            _refuse("RECRUITING_INPUT_MALFORMED", "a missing request names no dataset, integer parameters or reason")
        cells.append({"cell_key": rc.cell_key(request["dataset"], params), "dataset": request["dataset"],
                      "parameters": params, "state": "NOT_CAPTURED", "missing_reason": request["reason"],
                      "capture_id": None})
    if len({c["cell_key"] for c in cells}) != len(cells):
        _refuse("RECRUITING_INPUT_MALFORMED", "a requested cell repeats")
    if sorted(observations) != [str(s) for s in rc.RECRUIT_SEASONS]:
        _refuse("RECRUITING_INPUT_POPULATION_DRIFT", f"recruiting captures cover {sorted(observations)}, the release "
                                                     "layout is 2010-2017")
    cells.sort(key=lambda c: rc.cell_order(c["dataset"], c["parameters"]))
    inputs["acquisition_manifest"] = _spec("DATA_ROOT", acquisition_rel, acquisition_bytes)
    for name, manifest_rel in (("people", people_manifest_rel), ("core", core_manifest_rel)):
        manifest_bytes = _file_bytes(_located(repo, manifest_rel), manifest_rel)
        registry_manifest = _json_bytes(manifest_bytes, manifest_rel)
        payload = registry_manifest.get("payload") if isinstance(registry_manifest, dict) else None
        if not isinstance(payload, dict) or not isinstance(payload.get("external_relative_path"), str):
            _refuse("RECRUITING_INPUT_MALFORMED", f"{manifest_rel} names no registry payload")
        registry_rel = payload["external_relative_path"]
        registry_path = _located(data, registry_rel)
        if not _io_path(registry_path).is_file():
            _refuse("RECRUITING_INPUT_MISSING", f"{registry_rel}: no registry file")
        size, digest = _io_path(registry_path).stat().st_size, sha256_file(_io_path(registry_path))
        if (digest, size) != (payload.get("sha256"), payload.get("bytes")):
            _refuse("RECRUITING_INPUT_TAMPERED", f"{registry_rel} differs from its manifest's payload pin")
        inputs[f"{name}_registry"] = {"locator": "DATA_ROOT", "relative_path": registry_rel, "sha256": digest,
                                      "bytes": size}
        inputs[f"{name}_manifest"] = _spec("REPOSITORY", manifest_rel, manifest_bytes)
    rights_bytes = _file_bytes(_located(repo, rights_rel), rights_rel)
    try:
        rights_rows = list(csv.DictReader(rights_bytes.decode("utf-8").splitlines()))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise rc.RecruitingError("RECRUITING_INPUT_MALFORMED", f"{rights_rel}: {exc}") from exc
    chosen = [row for row in rights_rows if row.get("decision_id") == RIGHTS_DECISION_ID]
    if len(chosen) != 1 or chosen[0].get("source_id") != rc.SOURCE_ID:
        _refuse("RECRUITING_INPUT_MALFORMED", f"{rights_rel}: exactly one {RIGHTS_DECISION_ID} row is required")
    decision = {k: chosen[0].get(k) for k in RIGHTS_FIELDS}
    decision["row_sha256"] = sha256_bytes(rc.canonical_json_bytes(chosen[0]))
    inputs["rights_metadata"] = _spec("REPOSITORY", rights_rel, rights_bytes, decision=decision)
    legacy_bytes = _file_bytes(_located(data, legacy_rel), legacy_rel)
    inputs["legacy_people_builder"] = _spec("DATA_ROOT", legacy_rel, legacy_bytes)
    expected = {"cells": cells, "captures": dict(sorted(captures.items())),
                "observations": dict(sorted(observations.items())),
                "national_expected_universe": "NOT_ESTABLISHED",
                "counts": {"requested_cells": len(cells),
                           "captured_cells": sum(1 for c in cells if c["state"] == "CAPTURED"),
                           "not_captured_cells": sum(1 for c in cells if c["state"] != "CAPTURED"),
                           "observations": sum(o["rows"] for o in observations.values())}}
    return {name: inputs[name] for name in rc.input_names(inputs)}, expected


def make_contract(data_root: Path, repo_root: Path, frozen_at_utc: str, *, cycle_number: int = 64,
                  attempt_number: int = 1, jira_key: str = "BAT-735", **paths: str) -> dict[str, Any]:
    """The complete data contract (rules, pinned inputs and the source key universe), frozen before qualification."""
    if not (isinstance(frozen_at_utc, str) and rc.UTC_SECOND_RE.match(frozen_at_utc)):
        raise BuildRefused("ARGUMENT_INVALID", "--frozen-at must be YYYY-MM-DDTHH:MM:SSZ")
    inputs, expected = source_census(data_root, repo_root, **paths)
    return {"schema": CONTRACT_SCHEMA, "contract_id": rc.CONTRACT_ID, "population_id": rc.POPULATION,
            "cycle_number": cycle_number, "attempt_number": attempt_number, "jira_key": jira_key,
            "frozen_at_utc": frozen_at_utc, "outputs": {"database": rc.DB_FILE}, "labels": rc.LABELS,
            "rules": rc.rules_document(), "inputs": inputs, "expected": expected,
            "statement": "Frozen before any real qualification or canonical write: rules, schemas, record types, "
                         "identity and profile algorithms, the pinned source files and the source key universe "
                         "(requested cells, captures, observation keys). Derived qualification records and their "
                         "content, database and profile identities arise only in the first authorized build; a "
                         "separate pin of exactly those values follows. Manager readiness counts were known before "
                         "these rules (no blind claim)."}


def contract_bytes(contract: dict[str, Any]) -> bytes:
    return (json.dumps(contract, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def load_contract(path: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The contract, its SHA-256 and the anchors it binds; refuses any drift from the module's rules."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    for key, value in (("contract_id", rc.CONTRACT_ID), ("population_id", rc.POPULATION),
                       ("rules", rc.rules_document()), ("labels", rc.LABELS)):
        if rc.canonical_json_bytes(contract.get(key)) != rc.canonical_json_bytes(value):
            problems.append(key)
    if (contract.get("outputs") or {}).get("database") != rc.DB_FILE:
        problems.append("outputs.database")
    for key in ("inputs", "expected"):
        if not isinstance(contract.get(key), dict):
            problems.append(key)
    if not (isinstance(contract.get("frozen_at_utc"), str) and rc.UTC_SECOND_RE.match(contract["frozen_at_utc"])):
        problems.append("frozen_at_utc")
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the module's rules on {problems}")
    anchors = {"contract_id": contract["contract_id"], "contract_sha256": contract_sha,
               **{key: contract[key] for key in ANCHOR_KEYS}}
    return contract, contract_sha, anchors


# --------------------------------------------------------------------------------------------- inputs

def _ordered(items: list[Any], order: str) -> list[Any]:
    """Processing-order variants for the determinism proof: natural, reverse or shuffle:<seed>. They permute already
    indexed items only (every raw row keeps its original ordinal, every registry row its original row number)."""
    if order == "natural":
        return list(items)
    if order == "reverse":
        return list(reversed(items))
    if order.startswith("shuffle:") and order[len("shuffle:"):].isdigit():
        out = list(items)
        random.Random(int(order[len("shuffle:"):])).shuffle(out)
        return out
    raise BuildRefused("ARGUMENT_INVALID", f"input order must be natural, reverse or shuffle:<seed>, got {order!r}")


def resolve_inputs(data_root: Path, repo_root: Path, anchors: dict[str, Any]) -> dict[str, Path]:
    """Each pinned file, refused unless present with its pinned SHA-256 and bytes (literal locations first)."""
    roots = {"DATA_ROOT": _root(data_root), "REPOSITORY": _root(repo_root)}
    paths: dict[str, Path] = {}
    for name in rc.input_names(anchors["inputs"]):
        spec = anchors["inputs"][name]
        if spec.get("locator") not in roots:
            _refuse("RECRUITING_INPUT_LOCATION_UNSUPPORTED", f"{name}: locator {spec.get('locator')!r}")
        location = _located(roots[spec["locator"]], spec["relative_path"])
        if not _io_path(location).is_file():
            _refuse("RECRUITING_INPUT_MISSING", f"{name}: no file at {location}")
        size = _io_path(location).stat().st_size
        actual = sha256_file(_io_path(location))
        if actual != spec["sha256"] or size != spec["bytes"]:
            _refuse("RECRUITING_INPUT_TAMPERED", f"{name}: bytes hash to {actual} ({size} bytes), the contract pins "
                                                 f"{spec['sha256']} ({spec['bytes']} bytes)")
        paths[name] = location
    return paths


def _validate_row(row: Any, where: str) -> None:
    if not isinstance(row, dict):
        _refuse("RECRUITING_SOURCE_SCHEMA_INVALID", f"{where}: not a JSON object")
    for name in rc.SERVED_FIELDS:
        kind = rc.json_kind(row[name]) if name in row else "absent"
        if kind not in rc.RAW_KINDS[name]:
            _refuse("RECRUITING_SOURCE_SCHEMA_INVALID", f"{where}: {name} is a JSON {kind} (allowed: "
                                                        f"{list(rc.RAW_KINDS[name])})")
    if not rc.RECRUIT_ID_RE.match(row["id"]):
        _refuse("RECRUITING_SOURCE_SCHEMA_INVALID", f"{where}: id {row['id']!r} is not 1-12 ASCII digits")
    athlete = row.get("athleteId")
    if athlete is not None and not rc.ATHLETE_ID_RE.match(athlete):
        _refuse("RECRUITING_SOURCE_SCHEMA_INVALID", f"{where}: athleteId {athlete!r} is not an optionally signed "
                                                    "1-12 digit decimal string")
    rc.canonical_untrusted(row, "RECRUITING_SOURCE_SCHEMA_INVALID", where)


def observation_record(capture: dict[str, Any], season: int, ordinal: int, row: dict[str, Any]) -> dict[str, Any]:
    kinds = {name: (rc.json_kind(row[name]) if name in row else "absent") for name in rc.SERVED_FIELDS}
    return {"record_type": rc.RECORD_TYPES["observations"],
            "observation_key": rc.observation_key(capture["capture_id"], ordinal, row["id"]),
            "source_id": rc.SOURCE_ID, "dataset": rc.RECRUIT_DATASET, "capture_id": capture["capture_id"],
            "request_season": season, "raw_row_ordinal": ordinal,
            "raw_row_sha256": sha256_bytes(rc.canonical_json_bytes(row)), "raw_member_names": sorted(row),
            "absent_served_fields": sorted(name for name in rc.SERVED_FIELDS if name not in row),
            "source_field_kinds": kinds,
            **{rc.FIELD_NAMES[name]: (row[name] if name in row else None) for name in rc.SERVED_FIELDS},
            "capture_sha256": capture["response_sha256"], "receipt_sha256": capture["receipt_sha256"],
            **rc.RECORD_LABELS}


def _csv_rows(path: Path, columns: tuple[str, ...], name: str):
    try:
        handle = _io_path(path).open("r", encoding="utf-8", newline="")
    except OSError as exc:
        raise rc.RecruitingError("RECRUITING_INPUT_MALFORMED", f"{name}: {exc}") from exc
    with handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except (StopIteration, csv.Error, UnicodeDecodeError) as exc:
            raise rc.RecruitingError("RECRUITING_INPUT_MALFORMED", f"{name}: no header ({exc})") from exc
        if tuple(header) != columns:
            _refuse("RECRUITING_INPUT_MALFORMED", f"{name}: the header differs from the frozen registry columns")
        number = -1
        try:
            for number, values in enumerate(reader):
                if len(values) != len(columns):
                    _refuse("RECRUITING_INPUT_MALFORMED", f"{name} row {number}: {len(values)} fields")
                yield number, values
        except (csv.Error, UnicodeDecodeError) as exc:
            raise rc.RecruitingError("RECRUITING_INPUT_MALFORMED", f"{name} after row {number}: {exc}") from exc


def scan_people(path: Path, identity_keys: set[str], entity_keys: set[str], legacy_ids: set[str]) -> dict[str, Any]:
    """The exact person, source-mapping and legacy observation witnesses of the selected observations, and the PERSON
    row multiplicity of every slot and canonical id (whole-registry integrity scan; nothing else is retained)."""
    col = {c: i for i, c in enumerate(rc.PEOPLE_COLUMNS)}
    persons: dict[str, list[tuple[int, dict[str, str]]]] = {}
    mappings: dict[str, list[tuple[int, dict[str, str]]]] = {}
    legacies: dict[str, list[tuple[int, dict[str, str]]]] = {}
    slots: dict[str, int] = {}
    canonicals: dict[str, int] = {}
    for number, values in _csv_rows(path, rc.PEOPLE_COLUMNS, "people_registry"):
        record_type = values[col["record_type"]]
        if record_type == "PERSON":
            slot, canonical = values[col["assignment_slot"]], values[col["canonical_id"]]
            slots[slot] = slots.get(slot, 0) + 1
            canonicals[canonical] = canonicals.get(canonical, 0) + 1
            if values[col["identity_key"]] in identity_keys:
                persons.setdefault(values[col["identity_key"]], []).append(
                    (number, dict(zip(rc.PEOPLE_COLUMNS, values))))
        elif record_type == "SOURCE_MAPPING":
            if values[col["source_system_id"]] == rc.SOURCE_ID and values[col["source_entity_key"]] in entity_keys:
                mappings.setdefault(values[col["source_entity_key"]], []).append(
                    (number, dict(zip(rc.PEOPLE_COLUMNS, values))))
        elif record_type == "RECRUITING_OBSERVATION":
            if values[col["record_id"]] in legacy_ids:
                legacies.setdefault(values[col["record_id"]], []).append(
                    (number, dict(zip(rc.PEOPLE_COLUMNS, values))))
    return {"persons": persons, "mappings": mappings, "legacies": legacies, "slots": slots, "canonicals": canonicals}


def scan_core(path: Path, labels: set[str]) -> dict[str, Any]:
    """Every team ALIAS row whose alias equals a selected program label exactly, and every team ENTITY row."""
    col = {c: i for i, c in enumerate(rc.CORE_COLUMNS)}
    aliases: dict[str, list[tuple[int, dict[str, str]]]] = {}
    teams: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for number, values in _csv_rows(path, rc.CORE_COLUMNS, "core_registry"):
        if values[col["entity_type"]] != "team":
            continue
        if values[col["record_type"]] == "ALIAS" and values[col["alias"]] in labels:
            aliases.setdefault(values[col["alias"]], []).append((number, dict(zip(rc.CORE_COLUMNS, values))))
        elif values[col["record_type"]] == "ENTITY":
            teams.setdefault(values[col["canonical_id"]], []).append((number, dict(zip(rc.CORE_COLUMNS, values))))
    return {"aliases": aliases, "teams": teams}


def load_inputs(data_root: Path, repo_root: Path, anchors: dict[str, Any], *,
                input_order: str = "natural") -> dict[str, Any]:
    """Every pinned input, verified and parsed; the request-cell and capture universe re-derived from the original
    acquisition manifest must equal the contract's, and every raw row is decoded with its JSON kinds and checked against
    the frozen source schema before any observation exists. ``input_order`` permutes the processing order of the
    already-indexed captures and rows (no variant may change a byte)."""
    paths = resolve_inputs(data_root, repo_root, anchors)
    expected = anchors["expected"]
    inputs_view, census = source_census(
        data_root, repo_root, acquisition_rel=anchors["inputs"]["acquisition_manifest"]["relative_path"],
        people_manifest_rel=anchors["inputs"]["people_manifest"]["relative_path"],
        core_manifest_rel=anchors["inputs"]["core_manifest"]["relative_path"],
        rights_rel=anchors["inputs"]["rights_metadata"]["relative_path"],
        legacy_rel=anchors["inputs"]["legacy_people_builder"]["relative_path"])
    if rc.canonical_json_bytes(census) != rc.canonical_json_bytes(expected) or \
            rc.canonical_json_bytes(inputs_view) != rc.canonical_json_bytes(anchors["inputs"]):
        raise BuildRefused("RECRUITING_INPUT_POPULATION_DRIFT", "the source census of the original acquisition "
                                                                "manifest, receipts and arrays differs from the "
                                                                "contract's pinned universe")
    rows: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
    for season in _ordered(list(rc.RECRUIT_SEASONS), input_order):
        name = f"recruiting_players:{season}"
        capture = expected["captures"][anchors["inputs"][name]["capture_id"]]
        array = _json_bytes(_file_bytes(paths[name], name), name)
        indexed = list(enumerate(array))
        for ordinal, row in _ordered(indexed, input_order):
            _validate_row(row, f"{name} row {ordinal}")
            rows.append((season, ordinal, row, capture))
    return {"paths": {k: str(v) for k, v in paths.items()}, "rows": rows,
            "people_registry": paths["people_registry"], "core_registry": paths["core_registry"],
            "input_order": input_order}


# --------------------------------------------------------------------------------------------- qualification

def qualify(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    """Every observation's record and its one qualification, then the partitions, sources, summary and census."""
    observations = [observation_record(capture, season, ordinal, row)
                    for season, ordinal, row, capture in inputs["rows"]]
    order = inputs["input_order"]
    seen_recruit: set[str] = set()
    seen_athlete: set[str] = set()
    for o in sorted(observations, key=lambda o: (o["request_season"], o["raw_row_ordinal"])):
        if o["source_recruit_id"] in seen_recruit or (o["source_athlete_id"] is not None and
                                                      o["source_athlete_id"] in seen_athlete):
            raise BuildRefused("RECRUITING_SOURCE_DUPLICATE_ID", f"{o['observation_key']}: a source ID repeats")
        seen_recruit.add(o["source_recruit_id"])
        if o["source_athlete_id"] is not None:
            seen_athlete.add(o["source_athlete_id"])
    identity: dict[str, tuple[str, str, str]] = {}
    for o in observations:
        identity[o["observation_key"]] = rc.identity_key_for(o["source_athlete_id"], o["source_recruit_id"])
    people = scan_people(Path(inputs["people_registry"]), {i[1] for i in identity.values()},
                         {i[2] for i in identity.values()},
                         {rc.legacy_record_id(o["capture_id"], o["source_recruit_id"]) for o in observations})
    labels = {o["committed_to"] for o in observations if o["source_field_kinds"]["committedTo"] == "string"}
    core = scan_core(Path(inputs["core_registry"]), labels)
    registry_sha = anchors["inputs"]["core_registry"]["sha256"]
    captures = anchors["expected"]["captures"]
    qualifications, core_rows = [], {}
    for o in _ordered(observations, order):
        _namespace, key, entity = identity[o["observation_key"]]
        persons = [rc.person_witness(row, n, people["slots"].get(row["assignment_slot"], 0),
                                     people["canonicals"].get(row["canonical_id"], 0))
                   for n, row in people["persons"].get(key, [])]
        mappings = [rc.mapping_witness(row, n) for n, row in people["mappings"].get(entity, [])]
        legacies = [rc.legacy_witness(row, n) for n, row in
                    people["legacies"].get(rc.legacy_record_id(o["capture_id"], o["source_recruit_id"]), [])]
        alias_rows = core["aliases"].get(o["committed_to"], []) if \
            o["source_field_kinds"]["committedTo"] == "string" else []
        aliases = [rc.alias_view(rc.core_source_key(n, row["record_id"]), n, row) for n, row in alias_rows]
        candidates = {row["canonical_id"] for _n, row in alias_rows}
        team_rows = core["teams"].get(next(iter(candidates)), []) if len(candidates) == 1 else []
        teams = [rc.team_view(rc.core_source_key(n, row["record_id"]), n, row) for n, row in team_rows]
        for n, row in alias_rows:
            core_rows[(n, row["record_id"])] = ("CORE_TEAM_ALIAS_ROW", row)
        for n, row in team_rows:
            core_rows[(n, row["record_id"])] = ("CORE_TEAM_ENTITY_ROW", row)
        qualifications.append(rc.qualification_record(o, rc.canonical_line(o), captures[o["capture_id"]], persons,
                                                      mappings, legacies, aliases, teams))
    observations.sort(key=lambda o: (o["request_season"], o["raw_row_ordinal"]))
    qualifications.sort(key=lambda q: (q["request_season"], q["raw_row_ordinal"]))
    counts: dict[str, int] = {}
    for o in observations:
        counts[o["capture_id"]] = counts.get(o["capture_id"], 0) + 1
    partitions = rc.partition_records(anchors["expected"], counts)
    sources = rc.file_source_records(anchors) + [
        rc.core_source_record(n, row, kind, registry_sha) for (n, _rid), (kind, row) in sorted(core_rows.items())]
    derived = {"observations": observations, "qualifications": qualifications, "partitions": partitions,
               "sources": sources}
    derived["summary"] = rc.summary_rows(observations, qualifications)
    derived["census"] = [rc.census_record(derived)]
    return derived


def check_expected(derived: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    """The derivation's key universe must equal the contract's pinned universe (observed by the source census before
    any qualification); a difference is a refused population drift."""
    expected = anchors["expected"]
    differing = []
    for season, spec in expected["observations"].items():
        keys = [o["observation_key"] for o in derived["observations"] if str(o["request_season"]) == season]
        if len(keys) != spec["rows"] or rc.keys_sha256(keys) != spec["keys_sha256"]:
            differing.append(f"observations:{season}")
    if [p["partition_key"] for p in derived["partitions"]] != [c["cell_key"] for c in expected["cells"]]:
        differing.append("partitions")
    if differing:
        raise BuildRefused("RECRUITING_INPUT_POPULATION_DRIFT", f"the derivation differs from the contract's pinned "
                                                                f"universe on {differing}")
    return {"observations": len(derived["observations"]), "partitions": len(derived["partitions"]),
            "observation_seasons_equal": sorted(expected["observations"])}


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    """A hash-chained observation checkpoint: each chunk of canonical observations' record lines is written once
    (deterministic gzip) and its ledger row chains the prefix (the accepted C63/C61 builder's checkpoint, unchanged but
    for the schema)."""

    def __init__(self, directory: Path, header: dict[str, Any], chunk_size: int, resume: bool) -> None:
        self.dir = Path(directory)
        self.chunk_size = chunk_size
        self.ledger = self.dir / "checkpoint.ledger.jsonl"
        header_path = self.dir / "checkpoint.json"
        if resume:
            if not header_path.is_file():
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"no checkpoint header in {self.dir}")
            stored = json.loads(header_path.read_text(encoding="utf-8"))
            differing = sorted(k for k in set(stored) | set(header) if stored.get(k) != header.get(k))
            if differing:
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"checkpoint binds different {differing}")
        else:
            if self.dir.exists() and any(self.dir.iterdir()):
                raise BuildRefused("CHECKPOINT_EXISTS", f"{self.dir} is not empty; use --resume")
            (self.dir / "chunks").mkdir(parents=True, exist_ok=True)
            with header_path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(header, sort_keys=True, indent=1) + "\n")

    def chunk_path(self, index: int) -> Path:
        return self.dir / "chunks" / f"chunk_{index:06d}.gz"

    def completed(self, keys: list[str]) -> list[dict[str, Any]]:
        if not self.ledger.is_file():
            return []
        lines = self.ledger.read_text(encoding="utf-8").split("\n")
        rows = [json.loads(line) for line in lines[:-1] if line]  # a torn, unterminated last line is not complete
        prefix = ""
        for expected_index, row in enumerate(rows, start=1):
            start = (expected_index - 1) * self.chunk_size
            chunk_keys = keys[start:start + self.chunk_size]
            path = self.chunk_path(expected_index)
            if row.get("index") != expected_index or row.get("count") != len(chunk_keys) or not chunk_keys or \
                    row.get("keys_sha256") != _keys_sha(chunk_keys) or row.get("first_key") != chunk_keys[0] or \
                    row.get("last_key") != chunk_keys[-1]:
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"ledger row {expected_index} does not match the key prefix")
            if not path.is_file() or sha256_file(path) != row.get("chunk_sha256"):
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"chunk {expected_index} bytes differ from the ledger")
            prefix = sha256_bytes((prefix + row["chunk_sha256"]).encode("ascii"))
            if row.get("prefix_sha256") != prefix:
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"chained prefix breaks at chunk {expected_index}")
        return rows

    def write_chunk(self, index: int, keys: list[str], blob: bytes, previous_prefix: str) -> dict[str, Any]:
        path = self.chunk_path(index)
        if path.exists():  # written before an interruption but never recorded in the ledger
            if path.read_bytes() != blob:
                raise BuildRefused("REFUSED_FORKED_CHECKPOINT", f"unrecorded chunk {index} differs from the rebuild")
        else:
            temporary = path.with_suffix(".partial")
            if temporary.exists():
                raise BuildRefused("REFUSED_FORKED_CHECKPOINT", f"partial chunk {index} present")
            with temporary.open("xb") as handle:
                handle.write(blob)
            os.replace(temporary, path)
        chunk_sha = sha256_bytes(blob)
        row = {"index": index, "count": len(keys), "first_key": keys[0], "last_key": keys[-1],
               "keys_sha256": _keys_sha(keys), "chunk_sha256": chunk_sha,
               "prefix_sha256": sha256_bytes((previous_prefix + chunk_sha).encode("ascii"))}
        with self.ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row


def build_lines(derived: dict[str, Any], keys: list[str], *, chunk_size: int, checkpoint: Checkpoint | None,
                stop_after: int | None) -> dict[tuple[str, str], list[str]] | None:
    """The record lines of every per-season block, through the observation checkpoint when one is used (None when
    interrupted). The global partition, source, summary and census blocks follow unchanged."""
    blocks = {(table, segment): list(lines) for table, segment, _records, lines in rc.block_lines(derived)}
    if checkpoint is None:
        return blocks
    done = checkpoint.completed(keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    index, written = len(done), 0
    while index * chunk_size < len(keys):
        index += 1
        start = (index - 1) * chunk_size
        chunk_keys = keys[start:start + chunk_size]
        blob = gzip.compress(rc.observation_chunk(derived, chunk_keys), compresslevel=9, mtime=0)
        prefix = checkpoint.write_chunk(index, chunk_keys, blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(keys):
            return None
    rows = checkpoint.completed(keys)
    if sum(row["count"] for row in rows) != len(keys):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "the checkpoint does not cover every observation")
    out: dict[tuple[str, str], list[str]] = {key: [] for key in blocks if key[1] != "GLOBAL"}
    for row in rows:
        for entry in gzip.decompress(checkpoint.chunk_path(row["index"]).read_bytes()).decode("utf-8").splitlines():
            if not entry:
                continue
            table, segment, line = entry.split("\t", 2)
            out[(table, segment)].append(line)
    for key, lines in blocks.items():
        if key[1] == "GLOBAL":
            out[key] = lines
    return out


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any], db_path: Path,
                content_identity: str, content_doc: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = sha256_bytes(rc.canonical_json_bytes(identity_document))
    target = Path(output_root) / "sha256" / identity
    manifest = Path(manifest_root) / "sha256" / identity / "run_manifest.json"
    declared = identity_document["outputs"]
    state = "MATERIALIZED"
    if target.exists():
        present = sorted(p.name for p in target.iterdir())
        if present != sorted(declared) or any(sha256_file(target / name) != sha for name, sha in declared.items()):
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"{target} exists with different content")
        state = "ALREADY_PRESENT_IDENTICAL"
    else:
        temporary = Path(output_root) / "sha256" / f".tmp-{identity[:16]}-{os.getpid()}-{time.time_ns()}"
        temporary.mkdir(parents=True)
        data = Path(db_path).read_bytes()
        with (temporary / rc.DB_FILE).open("xb") as handle:
            handle.write(data)
        if sha256_file(temporary / rc.DB_FILE) != declared[rc.DB_FILE]:
            raise BuildRefused("WRITE_VERIFY_FAILED", rc.DB_FILE)
        os.rename(temporary, target)
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        # canonical bytes, never Python equality (an integral float count equals its integer there)
        if existing.get("identity") != identity or \
                rc.canonical_json_bytes(existing.get("identity_document")) != rc.canonical_json_bytes(identity_document) \
                or rc.canonical_json_bytes(existing.get("content_document")) != rc.canonical_json_bytes(content_doc):
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"{manifest} names a different identity")
        manifest_state = "ALREADY_PRESENT"
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"identity": identity, "identity_document": identity_document,
                                     "content_identity": content_identity, "content_document": content_doc,
                                     "provenance": provenance}, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        manifest_state = "WRITTEN"
    return {"identity": identity, "state": state, "data_dir": str(target), "manifest": str(manifest),
            "manifest_state": manifest_state}


def build(args: argparse.Namespace, loader: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha, anchors = load_contract(args.contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    load = loader or load_inputs
    try:
        inputs = load(args.data_root, args.repo_root, anchors, input_order=args.input_order)
        derived = qualify(inputs, anchors)
    except rc.RecruitingError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    expectation = check_expected(derived, anchors)
    keys = [o["observation_key"] for o in derived["observations"]]
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "inputs_sha256": {n: spec["sha256"] for n, spec in anchors["inputs"].items()},
                  "payload_schema": rc.PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                  "observation_list_sha256": _keys_sha(keys), "observation_count": len(keys),
                  "producer_sha256": sha256_file(Path(__file__)), "module_sha256": sha256_file(Path(rc.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = build_lines(derived, keys, chunk_size=args.chunk_size, checkpoint=checkpoint,
                        stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0,
                "observation_count": len(keys)}
    if built != {(t, s): list(lines) for t, s, _r, lines in rc.block_lines(derived)}:
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    document = rc.content_document(anchors, derived)
    content_identity = sha256_bytes(rc.canonical_json_bytes(document))
    meta = rc.meta_values(anchors, content_identity, derived)
    work_parent = Path(args.work_root) if args.work_root else None
    with tempfile.TemporaryDirectory(prefix="rce-", dir=work_parent) as work:
        db_path = Path(work) / rc.DB_FILE
        table_counts = rc.build_database(db_path, derived, meta)
        database_doc = rc.database_document(contract_sha, content_identity, sha256_file(db_path), table_counts)
        database_identity = sha256_bytes(rc.canonical_json_bytes(database_doc))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "module_path": str(Path(rc.__file__).resolve()),
                      "module_sha256": sha256_file(Path(rc.__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                      "chunk_size": args.chunk_size, "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "data_root": str(args.data_root), "content_identity": content_identity,
                      "database_identity": database_identity}
        result = materialize(args.output_root, args.manifest_root, database_doc, db_path, content_identity, document,
                             provenance)
    materialized_db = Path(result["data_dir"]) / rc.DB_FILE
    try:
        with rc.RecruitingEvidence(materialized_db, manifest=Path(result["manifest"]),
                                   anchors={**anchors, "profile": None}) as reader:
            reader_check = {"verified": True, "identity": reader.database_identity,
                            "content_identity": reader.content_identity, "qualifications_rederived": True}
    except rc.RecruitingError as exc:
        raise BuildRefused("MATERIALIZED_RELEASE_REFUSED_BY_READER", str(exc)) from exc
    production = {k: rc.ANCHORS.get(k) for k in ANCHOR_KEYS}
    profile = rc.RECRUITING_PROFILE
    return {"state": result["state"], "content_identity": content_identity, "database_identity": database_identity,
            "release": result, "reader_check": reader_check, "expected_collections": expectation,
            "census": derived["census"][0]["population"], "row_counts": document["row_counts"],
            "table_counts": table_counts, "database_sha256": database_doc["outputs"][rc.DB_FILE],
            "database_bytes": materialized_db.stat().st_size, "lines_sha256": document["lines_sha256"],
            "summary_sha256": meta["summary_sha256"], "census_sha256": meta["census_sha256"],
            "rules_sha256": rc.rules_sha256(), "contract_sha256": contract_sha, "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: anchors[k] for k in ANCHOR_KEYS} == production,
            "contract_pinned_by_reader": contract_sha == rc.ANCHORS.get("contract_sha256"),
            "profile_pinned": profile,
            "profile_reproduced": profile is not None and
            (profile.get("content_identity"), profile.get("database_identity")) == (content_identity, database_identity),
            "inputs": {n: {"sha256": spec["sha256"], "path": str((inputs.get("paths") or {}).get(n))}
                       for n, spec in anchors["inputs"].items()},
            "input_order": args.input_order, "chunk_size": args.chunk_size, "resumed": bool(args.resume),
            "variant": args.variant, "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser(repo_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_recruiting_evidence", allow_abbrev=False,
                                     description="Build the national recruiting evidence release 2010-2017.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path,
                        help="the data root holding every pinned DATA_ROOT input at the contract's relative locators")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=repo_root,
                        help="the checkout holding the pinned REPOSITORY witnesses (default: this checkout)")
    parser.add_argument("--input-order", default="natural")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--stop-after-chunks", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--work-root", type=Path, default=None,
                        help="parent directory of the temporary database (default: the system temporary root)")
    parser.add_argument("--variant", default="CANONICAL")
    parser.add_argument("--receipt", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None, loader: Callable[..., dict[str, Any]] | None = None, *,
         repo_root: Path | None = None, program: str = "tools/cycle64/build_national_recruiting_evidence.py") -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[3]
    args = build_parser(root).parse_args(raw)
    args.argv = [program, *raw]
    try:
        result = build(args, loader)
    except BuildRefused as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    text = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.receipt is not None:
        with Path(args.receipt).open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    sys.stdout.write(text)
    return INTERRUPTED_EXIT if result["state"] == "INTERRUPTED_AT_CHECKPOINT" else 0
