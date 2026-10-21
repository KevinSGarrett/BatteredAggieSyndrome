r"""Build machinery of the national retrospective site/calendar association release 2016-2023 (BAT-734, Cycle #63
TP63-A01): pinned input loading, the per-target source qualification, the parent witnesses, the contract checks and
the create-only, content-addressed materialization.

``python -B tools/cycle63/build_national_site_calendar_association.py
--contract configs/national_site_calendar_association_2016_2023_contract.json --data-root <data>
--output-root <data>/canonical/national_site_calendar_association_2016_2023
--manifest-root <data>/manifests/national_site_calendar_association_2016_2023``

Every input is a whole file pinned by SHA-256 and byte count in the committed contract, at a relative locator under the
explicitly named data root; the data root and every resolved location pass the BAT-717 literal local-file policy before
any filesystem access, and nothing is ever written there. The accepted parents are read directly after their whole-file
pin verifies (their manifests must name the pinned identity and bytes): the C39 history targets, history views and the
C56 reference feature, label and parent game-score blocks (each block's index re-checked) for 2016-2023 only, the C38
contest rows of 2016-2023 only, the C38 participant identity bindings and the eight provider game captures with their
capture receipts. Hashing a whole parent file reads its 2024/2025 bytes too; no 2024/2025 target, feature, label,
design, fit or score is ever selected or derived.

The builder refuses unless the contract's rules equal :func:`context_association.rules_document`, every parent contract
of this checkout hashes to its pin and every input verifies. It qualifies every target from the raw inputs (source only:
no fit), derives every grain with :func:`context_association.derive_from_qualifications` (the two frozen fits
included), refuses a derivation whose key collections, frozen common cohort or parent witnesses differ from the
contract's expected ones (population drift, never forced), writes the deterministic SQLite database and materializes it
create-only: an existing identity is verified, never rewritten, and differing bytes at an existing identity are refused.
The materialized database is then opened through the reader's complete verification with the contract's anchors.
``--input-order`` (natural, reverse, shuffle:<seed>), ``--chunk-size`` with ``--checkpoint-dir`` and
``--stop-after-chunks``/``--resume`` prove that order, chunking and an interrupted build cannot change a byte. No source
request, activation, admission, model search or default change is made.

Adapted from the accepted Cycle 61 builder (its checkpoint, order, materialization and receipt machinery) and the
accepted Cycle 58 game-context provider join (generalized from 2023 to the eight study seasons).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
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
from aggie_analytics.retrospective_baseline import context_association as ca
from aggie_analytics.retrospective_baseline import reference_fit as rf

PRODUCER = "national_site_calendar_association_2016_2023/1.0.0"
CHECKPOINT_SCHEMA = "BAS-SITE-CALENDAR-ASSOCIATION-CHECKPOINT-1"
INTERRUPTED_EXIT = 3
ANCHOR_KEYS = ("inputs", "parent_contracts", "expected")
SINGLE_INPUTS = ("population_database", "population_manifest", "participant_bindings", "history_database",
                 "history_manifest", "reference_database", "reference_manifest")
SEASONAL_INPUTS = ("provider_games", "capture_receipts")
CONTEST_COLUMNS = ("contest_key", "season", "contest_date", "site", "neutral_site_text", "a_key", "b_key", "a_org_id",
                   "b_org_id", "cfbd_game_ids")
REFERENCE_TABLES = ("features", "labels", "scores")


class BuildRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise ca.ContextError(code, message)


sha256_bytes = ca.sha256_bytes
sha256_file = ca.sha256_file
_io_path = ca._io_path


# --------------------------------------------------------------------------------------------- inputs

def _ordered(items: list[Any], order: str) -> list[Any]:
    """Input order variants for the determinism proof: natural, reverse or shuffle:<seed>."""
    if order == "natural":
        return list(items)
    if order == "reverse":
        return list(reversed(items))
    if order.startswith("shuffle:") and order[len("shuffle:"):].isdigit():
        out = list(items)
        random.Random(int(order[len("shuffle:"):])).shuffle(out)
        return out
    raise BuildRefused("ARGUMENT_INVALID", f"input order must be natural, reverse or shuffle:<seed>, got {order!r}")


def _literal(path: Path, code_prefix: str) -> str:
    try:
        return readonly_sqlite.literal_path(path)
    except readonly_sqlite.DatabaseLocationError as exc:
        suffix = "UNSUPPORTED" if exc.code == readonly_sqlite.LOCATION_UNSUPPORTED else "NOT_LITERAL"
        raise ca.ContextError(f"{code_prefix}_LOCATION_{suffix}", exc.detail) from exc


def _input_specs(anchors: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    specs = anchors["inputs"]
    out = [(name, specs[name]) for name in SINGLE_INPUTS]
    for group in SEASONAL_INPUTS:
        out += [(f"{group}:{season}", spec) for season, spec in sorted(specs[group].items())]
    return out


def resolve_inputs(data_root: Path, anchors: dict[str, Any]) -> dict[str, Path]:
    """Each pinned file under the explicitly named data root, refused unless present with its pinned SHA-256 and bytes.
    The root and every resolved location pass the BAT-717 literal local-file policy before any access."""
    root = Path(_literal(Path(data_root), "CONTEXT_DATA_ROOT"))
    if not _io_path(root).is_dir():
        _refuse("CONTEXT_DATA_ROOT_MISSING", f"no data root directory at {data_root}")
    paths: dict[str, Path] = {}
    for name, spec in _input_specs(anchors):
        location = Path(_literal(root / Path(*spec["relative_path"].split("/")), "CONTEXT_INPUT"))
        if not _io_path(location).is_file():
            _refuse("CONTEXT_INPUT_MISSING", f"{name}: no file at {location}")
        size = _io_path(location).stat().st_size
        actual = sha256_file(_io_path(location))
        if actual != spec["sha256"] or size != spec["bytes"]:
            _refuse("CONTEXT_INPUT_TAMPERED", f"{name}: bytes hash to {actual} ({size} bytes), the contract pins "
                                              f"{spec['sha256']} ({spec['bytes']} bytes)")
        paths[name] = location
    return paths


def _connect(path: Path) -> sqlite3.Connection:
    try:
        return readonly_sqlite.connect_readonly(_io_path(path), immutable=True)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise ca.ContextError("CONTEXT_INPUT_MALFORMED", f"{path}: {exc.detail}") from exc
    except sqlite3.Error as exc:
        raise ca.ContextError("CONTEXT_INPUT_MALFORMED", f"{path}: {exc}") from exc


def _json_file(path: Path) -> Any:
    try:
        return json.loads(_io_path(path).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ca.ContextError("CONTEXT_INPUT_MALFORMED", f"{path}: {exc}") from exc


def _manifest_check(name: str, path: Path, spec: dict[str, Any], database_spec: dict[str, Any],
                    database_file: str) -> None:
    doc = _json_file(path)
    outputs = ((doc.get("identity_document") or {}).get("outputs") or {}) if isinstance(doc, dict) else {}
    if not isinstance(doc, dict) or doc.get("identity") != spec["identity"] or \
            spec["identity"] != database_spec["identity"] or outputs.get(database_file) != database_spec["sha256"]:
        _refuse("CONTEXT_PARENT_IDENTITY_MISMATCH", f"{name}: the manifest does not name the pinned identity and bytes")


def _reference_blocks(conn: sqlite3.Connection) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    out: dict[str, list[tuple[str, dict[str, Any]]]] = {t: [] for t in REFERENCE_TABLES}
    seasons = [str(s) for s in ca.STUDY_SEASONS]
    rows = conn.execute(f"SELECT record_table, segment, records, first_key, last_key, lines_sha256, block FROM blocks "
                        f"WHERE record_table IN ({', '.join('?' for _ in REFERENCE_TABLES)}) AND segment IN "
                        f"({', '.join('?' for _ in seasons)}) ORDER BY ord", (*REFERENCE_TABLES, *seasons)).fetchall()
    for table, segment, records, _first, _last, lines_sha, blob in rows:
        try:
            data = zlib.decompress(blob)
            lines = data.decode("utf-8").split("\n")
        except (zlib.error, TypeError, UnicodeDecodeError) as exc:
            raise ca.ContextError("CONTEXT_INPUT_MALFORMED", f"reference {table} {segment}: {exc}") from exc
        if lines[-1] != "" or sha256_bytes(data) != lines_sha or records != len(lines) - 1:
            _refuse("CONTEXT_INPUT_MALFORMED", f"reference {table} {segment}: the block index differs from its content")
        for line in lines[:-1]:
            record = json.loads(line)
            if not isinstance(record, dict) or str(record.get("season")) != segment:
                _refuse("CONTEXT_INPUT_MALFORMED", f"reference {table} {segment}: a record of another season")
            out[table].append((line, record))
    return out


def load_inputs(data_root: Path, anchors: dict[str, Any], *, input_order: str = "natural") -> dict[str, Any]:
    """Every pinned input, verified and parsed; ``input_order`` permutes every loaded collection before the
    qualification (which indexes by key and orders canonically, so no variant may change a byte)."""
    paths = resolve_inputs(data_root, anchors)
    specs = anchors["inputs"]
    first, last = ca.STUDY_SEASONS[0], ca.STUDY_SEASONS[-1]
    for name, database, file_name in (("population_manifest", "population_database", None),
                                      ("history_manifest", "history_database", None),
                                      ("reference_manifest", "reference_database", None)):
        _manifest_check(name, paths[name], specs[name], specs[database], file_name or paths[database].name)
    try:
        conn = _connect(paths["history_database"])
        try:
            hmeta = dict(conn.execute("SELECT key, value FROM meta"))
            targets = [(r[0], json.loads(r[0])) for r in conn.execute(
                "SELECT record FROM targets WHERE season BETWEEN ? AND ? ORDER BY ord", (first, last))]
            views = [(r[0], json.loads(r[0])) for r in conn.execute(
                "SELECT record FROM history WHERE season BETWEEN ? AND ? ORDER BY ord", (first, last))]
        finally:
            conn.close()
        conn = _connect(paths["population_database"])
        try:
            pmeta = dict(conn.execute("SELECT key, value FROM meta"))
            contests = [dict(zip(CONTEST_COLUMNS, r)) for r in conn.execute(
                f"SELECT {', '.join(CONTEST_COLUMNS)} FROM contest WHERE season BETWEEN ? AND ? ORDER BY contest_key",
                (first, last))]
        finally:
            conn.close()
        conn = _connect(paths["reference_database"])
        try:
            rmeta = dict(conn.execute("SELECT key, value FROM meta"))
            reference = _reference_blocks(conn)
        finally:
            conn.close()
        raw = gzip.decompress(_io_path(paths["participant_bindings"]).read_bytes()).decode("utf-8").split("\n")
        header = json.loads(raw[0])
        bindings = [(number, line, json.loads(line)) for number, line in enumerate(raw[1:], start=2) if line]
    except (sqlite3.DatabaseError, OSError, UnicodeDecodeError, ValueError, TypeError, KeyError, EOFError) as exc:
        if isinstance(exc, ca.ContextError):
            raise
        raise ca.ContextError("CONTEXT_INPUT_MALFORMED", f"{type(exc).__name__}: {exc}") from exc
    h, p, r = specs["history_database"], specs["population_database"], specs["reference_database"]
    if (hmeta.get("content_identity"), hmeta.get("contract_sha256"), hmeta.get("prior_rule")) != \
            (h["content_identity"], h["contract_sha256"], ca.PRIOR_RULE):
        _refuse("CONTEXT_PARENT_IDENTITY_MISMATCH", "the history meta names another content, contract or prior rule")
    if (pmeta.get("contract_sha256"), pmeta.get("program_season_identity")) != \
            (p["contract_sha256"], p["program_season_identity"]):
        _refuse("CONTEXT_PARENT_IDENTITY_MISMATCH", "the population meta names another contract or program season")
    if (rmeta.get("content_identity"), rmeta.get("contract_sha256")) != (r["content_identity"], r["contract_sha256"]):
        _refuse("CONTEXT_PARENT_IDENTITY_MISMATCH", "the reference meta names another content or contract")
    if not isinstance(header, dict) or (header.get("_header") or {}).get("contract_sha256") != \
            specs["participant_bindings"]["header_contract_sha256"]:
        _refuse("CONTEXT_PARENT_IDENTITY_MISMATCH", "the identity bindings header names another population contract")
    games: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    receipts: dict[int, dict[str, Any]] = {}
    if sorted(specs["provider_games"]) != sorted(specs["capture_receipts"]) or \
            not set(specs["provider_games"]) <= {str(s) for s in ca.STUDY_SEASONS}:
        _refuse("CONTEXT_INPUT_MALFORMED", "every pinned provider capture needs exactly one capture receipt of a study "
                                           "season")
    for season_text, spec in specs["provider_games"].items():
        rows = _json_file(paths[f"provider_games:{season_text}"])
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows) or len(rows) != spec["rows"]:
            _refuse("CONTEXT_INPUT_MALFORMED", f"provider games {season_text}: not the pinned list of objects")
        games[int(season_text)] = list(enumerate(rows))
    for season_text, spec in specs["capture_receipts"].items():
        receipt = _json_file(paths[f"capture_receipts:{season_text}"])
        params = (receipt.get("parameters") or {}) if isinstance(receipt, dict) else {}
        game_spec = specs["provider_games"].get(season_text) or {}
        if not isinstance(receipt, dict) or (
                receipt.get("capture_id"), receipt.get("response_sha256"), receipt.get("capture_known_at_utc"),
                receipt.get("retrieved_at_utc"), receipt.get("source_uri"), receipt.get("upstream_lineage"),
                receipt.get("result"), receipt.get("http_status"), receipt.get("row_count"),
                receipt.get("response_bytes"), params.get("year"), params.get("classification")) != (
                spec["capture_id"], game_spec.get("sha256"), spec["capture_known_at_utc"], spec["retrieved_at_utc"],
                spec["source_uri"], spec["upstream_lineage"], "SUCCESS", 200, game_spec.get("rows"),
                game_spec.get("bytes"), season_text, "fbs"):
            _refuse("CONTEXT_INPUT_MALFORMED", f"capture receipt {season_text}: not the pinned receipt of its capture")
        receipts[int(season_text)] = {**spec, "sha256": spec["sha256"]}
    order = input_order
    return {"paths": {k: str(v) for k, v in paths.items()}, "targets": _ordered(targets, order),
            "views": _ordered(views, order), "contests": _ordered(contests, order),
            "reference": {t: _ordered(v, order) for t, v in reference.items()},
            "bindings": _ordered(bindings, order),
            "games": {s: _ordered(v, order) for s, v in games.items()}, "receipts": receipts}


# --------------------------------------------------------------------------------------------- 1. qualification

def _index(items: list[Any], key: Callable[[Any], Any]) -> dict[Any, list[Any]]:
    out: dict[Any, list[Any]] = {}
    for item in items:
        k = key(item)
        if k is not None:
            out.setdefault(k, []).append(item)
    return out


def _binding(org_id: Any, index: dict[Any, list[tuple[int, str, dict[str, Any]]]]) -> dict[str, Any]:
    found = sorted(index.get(org_id, []), key=lambda item: item[0]) if isinstance(org_id, str) else []
    empty = {"cfbd_team_id": None, "rule": None, "line_number": None, "line_sha256": None}
    if not found:
        return {"state": "UNSUPPORTED", "reason": "NO_ACCEPTED_PARTICIPANT_BINDING", **empty}
    number, line, row = found[0]
    witness = {"line_number": number, "line_sha256": sha256_bytes(line.encode("utf-8"))}
    if len(found) > 1:
        return {"state": "UNSUPPORTED", "reason": "BINDING_DUPLICATED", **empty, **witness}
    cfbd, rule = row.get("cfbd_team_id"), row.get("rule")
    if not (isinstance(cfbd, str) and ca.DIGITS_RE.match(cfbd)) or rule not in ca.ACCEPTED_BINDING_RULES:
        return {"state": "UNSUPPORTED", "reason": "BINDING_NOT_CONFIRMED", **empty, **witness,
                "rule": rule if isinstance(rule, str) else None}
    return {"state": "BOUND", "reason": None, "cfbd_team_id": cfbd, "rule": rule, **witness}


def _game_shape_ok(row: dict[str, Any]) -> bool:
    return (all(ca.is_int(row.get(k)) for k in ("id", "season", "homeId", "awayId")) and
            isinstance(row.get("neutralSite"), bool) and isinstance(row.get("startTimeTBD"), bool) and
            isinstance(row.get("startDate"), str))


def _documented(target: dict[str, Any], parent: dict[str, Any]) -> tuple[list[str] | None, str | None]:
    ids = target.get("cfbd_game_ids")
    if not isinstance(ids, list) or not all(isinstance(x, str) and ca.DIGITS_RE.match(x) for x in ids):
        return None, "DOCUMENTED_GAME_IDS_MALFORMED"
    try:
        parent_ids = json.loads(parent["cfbd_game_ids"]) if isinstance(parent["cfbd_game_ids"], str) else None
    except ValueError:
        parent_ids = None
    if parent_ids != ids:
        return ids, "DOCUMENTED_GAME_IDS_DIFFER_FROM_PARENT"
    if not ids:
        return ids, "NO_DOCUMENTED_PROVIDER_GAME"
    if len(ids) > 1:
        return ids, "MULTIPLE_DOCUMENTED_PROVIDER_GAMES"
    return ids, None


def _provider(target: dict[str, Any], parent: dict[str, Any], sides: dict[str, dict[str, Any]],
              games: dict[int, list[tuple[int, dict[str, Any]]]], capture_sha: str | None) -> dict[str, Any]:
    ids, reason = _documented(target, parent)
    out: dict[str, Any] = {"documented": ids or [], "block": None, "state": "UNSUPPORTED", "reason": reason,
                           "home_side": None}
    if reason is not None:
        return out
    if capture_sha is None:
        out["reason"] = "NO_PINNED_CAPTURE_FOR_SEASON"
        return out
    found = games.get(int(ids[0]), [])
    if not found:
        out["reason"] = "PROVIDER_GAME_ABSENT_FROM_CAPTURE"
        return out
    if len(found) > 1:
        out["reason"] = "PROVIDER_GAME_ID_DUPLICATED"
        return out
    ordinal, row = found[0]
    if not _game_shape_ok(row):
        out["reason"] = "PROVIDER_FIELD_MALFORMED"
        return out
    out["block"] = {"capture_season": target["season"], "capture_sha256": capture_sha, "row_ordinal": ordinal,
                    "game_id": str(row["id"]), "season": row["season"], "home_id": str(row["homeId"]),
                    "away_id": str(row["awayId"]), "neutral_site": row["neutralSite"],
                    "start_claim_utc": row["startDate"], "start_time_tbd": row["startTimeTBD"],
                    "row_sha256": sha256_bytes(ca.canonical_json_bytes(row))}
    if row["season"] != target["season"]:
        out["reason"] = "PROVIDER_SEASON_DIFFERS"
        return out
    if any(sides[v]["state"] != "BOUND" for v in ca.VIEWS) or sides["A"]["cfbd_team_id"] == sides["B"]["cfbd_team_id"]:
        out["reason"] = "PARTICIPANT_BINDING_UNSUPPORTED"
        return out
    if {str(row["homeId"]), str(row["awayId"])} != {sides["A"]["cfbd_team_id"], sides["B"]["cfbd_team_id"]}:
        out["reason"] = "PROVIDER_PARTICIPANTS_DIFFER"
        return out
    out.update(state="PROVIDER_GAME_JOINED", reason=None,
               home_side="A" if str(row["homeId"]) == sides["A"]["cfbd_team_id"] else "B")
    return out


def _lineage(team_key: str, season: int, target_date: str, contributing: list[dict[str, Any]],
             contests: dict[str, dict[str, Any]]) -> str | None:
    """None when every eligible prior joins its own parent contest; else the first failing reason."""
    for entry in contributing:
        parent = contests.get(entry.get("contest_key"))
        if parent is None:
            return "PRIOR_PARENT_CONTEST_ABSENT"
        if parent["season"] != season:
            return "PRIOR_SEASON_DIFFERS"
        if parent["contest_date"] != entry.get("contest_date"):
            return "PRIOR_DATE_DIFFERS"
        if not (isinstance(entry.get("contest_date"), str) and entry["contest_date"] < target_date):
            return "PRIOR_NOT_STRICTLY_EARLIER"
        if team_key not in (parent["a_key"], parent["b_key"]):
            return "PRIOR_TEAM_NOT_PARTICIPANT"
    return None


def _counts(side: dict[str, Any]) -> tuple[int, int, int, int, list[str]]:
    keys = [c["contest_key"] for c in side["contributing"]]
    return side["games"], side["wins"], side["losses"], side["ties"], keys


def qualify(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    """Every accepted target's qualification record (source only, no fit), its accepted label and its five unchanged
    parent witnesses."""
    specs = anchors["inputs"]
    identities = {"history_identity": specs["history_database"]["identity"],
                  "population_identity": specs["population_database"]["identity"],
                  "reference_identity": specs["reference_database"]["identity"]}
    contests: dict[str, dict[str, Any]] = {}
    for row in inputs["contests"]:
        if row["contest_key"] in contests:
            _refuse("CONTEXT_INPUT_INVALID", f"parent contest {row['contest_key']} repeats")
        contests[row["contest_key"]] = row
    views: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    for text, record in inputs["views"]:
        key = (record.get("target_contest_key"), record.get("view"))
        if key in views:
            _refuse("CONTEXT_INPUT_INVALID", f"history view {key} repeats")
        views[key] = (text, record)
    ref = inputs["reference"]
    features = {(r["contest_key"], r["view"]): (line, r) for line, r in ref["features"]}
    labels = {r["contest_key"]: (line, r) for line, r in ref["labels"]}
    scores = {(r["contest_key"], r["model_id"]): (line, r) for line, r in ref["scores"]}
    if len(features) != len(ref["features"]) or len(labels) != len(ref["labels"]) or \
            len(scores) != len(ref["scores"]):
        _refuse("CONTEXT_INPUT_INVALID", "a reference record repeats")
    bindings = _index(inputs["bindings"], lambda item: item[2].get("org_id"))
    game_index = {season: _index(rows, lambda item: item[1].get("id") if ca.is_int(item[1].get("id")) else None)
                  for season, rows in inputs["games"].items()}
    receipts = inputs["receipts"]
    quals, label_map, witnesses, seen = [], {}, [], set()
    for text, target in inputs["targets"]:
        key, season, date = target.get("contest_key"), target.get("season"), target.get("contest_date")
        if key in seen:
            _refuse("CONTEXT_INPUT_INVALID", f"target {key} repeats")
        seen.add(key)
        if season not in ca.STUDY_SEASONS or not (isinstance(key, str) and ca.CONTEST_KEY_RE.match(key)) or \
                not ca.valid_date(date):
            _refuse("CONTEXT_INPUT_INVALID", f"target {key!r}: not a 2016-2023 study target")
        parent = contests.get(key)
        view_pair = [views.get((key, v)) for v in ca.VIEWS]
        feature_pair = [features.get((key, v)) for v in ca.VIEWS]
        label = labels.get(key)
        if parent is None or None in view_pair or None in feature_pair or label is None:
            _refuse("CONTEXT_INPUT_INVALID", f"{key}: the parent contest, a history view, a reference feature or the "
                                             "label is absent")
        (fa_line, fa), (fb_line, fb) = feature_pair
        (va_text, va), (vb_text, vb) = view_pair
        label_line, lab = label
        # exact parent/history/label identity (refused, never a support reason: the accepted parents must agree)
        if (parent["season"], parent["contest_date"], parent["a_key"], parent["b_key"], parent["site"]) != \
                (season, date, target["a_key"], target["b_key"], target["parent_site"]) or \
                (fa["season"], fa["contest_date"], fa["team_key"], fa["opponent_key"], fa["target_site"]) != \
                (season, date, target["a_key"], target["b_key"], parent["site"]) or \
                (fb["team_key"], fb["opponent_key"]) != (target["b_key"], target["a_key"]) or \
                (va["team_key"], va["opponent_key"], vb["team_key"], vb["opponent_key"]) != \
                (target["a_key"], target["b_key"], target["b_key"], target["a_key"]) or \
                (lab["a_key"], lab["b_key"], lab["season"]) != (target["a_key"], target["b_key"], season):
            _refuse("CONTEXT_INPUT_INVALID", f"{key}: the accepted target, parent row, history views, reference "
                                             "features and label disagree")
        for view_text, feature in ((va_text, fa), (vb_text, fb)):
            if feature["source_history"]["record_sha256"] != sha256_bytes(view_text.encode("utf-8")):
                _refuse("CONTEXT_INPUT_INVALID", f"{key}: a reference feature names another history view")
        for view, own, other in ((va, fa["team"], fa["opponent"]), (vb, fb["team"], fb["opponent"])):
            th, oh = view["team_history"], view["opponent_history"]
            for hist, block in ((th, own), (oh, other)):
                if (hist["games"], hist["wins"], hist["losses"], hist["ties"], hist["contributing_contest_keys"]) != \
                        _counts(block):
                    _refuse("CONTEXT_INPUT_INVALID", f"{key}: a reference feature history differs from its accepted "
                                                     "history view")
        label_sha = sha256_bytes(label_line.encode("utf-8"))
        state = lab["label_state"]
        y_a = lab.get("y_a")
        if state not in ca.LABEL_STATES or (state == "DECISIVE" and (not ca.is_int(y_a) or y_a not in (0, 1))):
            _refuse("CONTEXT_INPUT_INVALID", f"{key}: label state {state!r} is not an accepted state with its outcome")
        label_map[key] = {"label_state": state, "y_a": y_a if state == "DECISIVE" else None,
                          "record_sha256": label_sha}
        sides = {"A": _binding(target.get("a_org_id"), bindings), "B": _binding(target.get("b_org_id"), bindings)}
        receipt = receipts.get(season)
        provider = _provider(target, parent, sides, game_index.get(season, {}),
                             None if receipt is None else anchors["inputs"]["provider_games"][str(season)]["sha256"])
        joined = provider["state"] == "PROVIDER_GAME_JOINED"
        claim = ca.site_claim(provider["block"]["neutral_site"], provider["home_side"]) if joined else None
        agreement = ca.site_agreement(parent["site"], claim) if joined else "UNSUPPORTED"
        if joined:
            d_state, d_reason, offset = ca.date_state(provider["block"]["start_claim_utc"], date)
        else:
            d_state, d_reason, offset = "UNSUPPORTED", "PROVIDER_GAME_NOT_JOINED", None
        clock = None
        if provider["block"] is not None:
            clock = {"capture_id": receipt["capture_id"], "receipt_sha256": receipt["sha256"],
                     "response_sha256": provider["block"]["capture_sha256"],
                     "capture_known_at_utc": receipt["capture_known_at_utc"],
                     "retrieved_at_utc": receipt["retrieved_at_utc"], "source_uri": receipt["source_uri"],
                     "upstream_lineage": receipt["upstream_lineage"],
                     "observed_after_target": receipt["retrieved_at_utc"][:10] > date}
        calendars = {}
        for side, view in (("a", va), ("b", vb)):
            hist = view["team_history"]
            contributing = hist["contributing"]
            lineage = _lineage(view["team_key"], season, date, contributing, contests)
            excluded = [e.get("contest_date") for e in hist.get("excluded_inputs") or []]
            calendars[side] = ca.calendar_block([(c["contest_key"], c["contest_date"]) for c in contributing],
                                                [d for d in excluded if isinstance(d, str)] +
                                                [""] * sum(1 for d in excluded if not isinstance(d, str)),
                                                date, lineage)
        a_counts, b_counts = _counts(fa["team"]), _counts(fa["opponent"])
        q = {"record_type": ca.RECORD_TYPES["qualifications"], "qualification_key": key, "contest_key": key,
             "season": season, "contest_date": date, "partition": ca.partition_of(season), "a_key": target["a_key"],
             "b_key": target["b_key"], "a_org_id": target["a_org_id"], "b_org_id": target["b_org_id"],
             "a_team_name": target["a_team_name"], "b_team_name": target["b_team_name"],
             "parent_site": parent["site"], "parent_neutral_site_text": parent["neutral_site_text"],
             "documented_provider_game_ids": list(provider["documented"]), "a_binding": sides["A"],
             "b_binding": sides["B"], "provider": provider["block"], "provider_state": provider["state"],
             "provider_reason": provider["reason"], "provider_home_side": provider["home_side"],
             "provider_site_claim": claim, "site_agreement": agreement,
             "agreed_site": parent["site"] if agreement == "AGREE" else None, "date_state": d_state,
             "date_reason": d_reason, "provider_utc_date_offset_days": offset, "capture_clock": clock,
             "a_history": ca.history_block(*a_counts), "b_history": ca.history_block(*b_counts),
             "a_calendar": calendars["a"], "b_calendar": calendars["b"], "label_state": label_map[key]["label_state"],
             "label_record_sha256": label_sha}
        support, reasons, pattern = ca.support_decision(q)
        q.update(support_state=support, support_reasons=reasons, support_pattern=pattern,
                 target_record_sha256=sha256_bytes(text.encode("utf-8")),
                 parent_contest_sha256=sha256_bytes(ca.canonical_json_bytes(parent)),
                 history_view_sha256=[sha256_bytes(va_text.encode("utf-8")), sha256_bytes(vb_text.encode("utf-8"))],
                 reference_feature_sha256=[sha256_bytes(fa_line.encode("utf-8")), sha256_bytes(fb_line.encode("utf-8"))],
                 **identities, **ca.RECORD_LABELS)
        quals.append(q)
        for model_id in ca.PARENT_MODELS:
            found = scores.get((key, model_id))
            if found is None:
                _refuse("CONTEXT_INPUT_INVALID", f"{key}/{model_id}: no accepted parent game score")
            line, parent_score = found
            if parent_score.get("model_sha256") != ca.PARENT_MODEL_SHA256[model_id] or \
                    parent_score.get("metric_kind") != ca.metric_kind(model_id) or \
                    parent_score.get("orientation") != "A" or parent_score.get("label_record_sha256") != label_sha or \
                    ca.canonical_line(parent_score) != line:
                _refuse("CONTEXT_INPUT_INVALID", f"{key}/{model_id}: the accepted parent game score is not the frozen "
                                                 "comparator of this game")
            witnesses.append(ca.witness_record(parent_score, line, q, specs["reference_database"]["identity"]))
    quals.sort(key=ca._game_order)
    return {"qualifications": quals, "labels": label_map, "witnesses": witnesses}


def derive(inputs: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    qualified = qualify(inputs, anchors)
    return ca.derive_from_qualifications(qualified["qualifications"], qualified["labels"], qualified["witnesses"])


# --------------------------------------------------------------------------------------------- contract

def load_contract(path: Path, repo_root: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The contract, its SHA-256 and the anchors it binds; refuses any drift from the module's rules and any parent
    contract of this checkout that differs from its pin."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    for key, value in (("contract_id", ca.CONTRACT_ID), ("population_id", ca.POPULATION),
                       ("rules", ca.rules_document())):
        if ca.canonical_json_bytes(contract.get(key)) != ca.canonical_json_bytes(value):
            problems.append(key)
    if (contract.get("outputs") or {}).get("database") != ca.DB_FILE:
        problems.append("outputs.database")
    for key in ANCHOR_KEYS:
        if not isinstance(contract.get(key), dict):
            problems.append(key)
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the module's rules on {problems}")
    for rel, want in contract["parent_contracts"].items():
        local = Path(repo_root) / Path(*rel.split("/"))
        if not local.is_file() or sha256_file(local) != want:
            raise BuildRefused("PARENT_CONTRACT_MISMATCH", f"{rel}: the checkout's bytes differ from the pin")
    anchors = {"contract_id": contract["contract_id"], "contract_sha256": contract_sha,
               **{key: contract[key] for key in ANCHOR_KEYS}}
    return contract, contract_sha, anchors


def expected_from_qualification(qualified: dict[str, Any]) -> dict[str, Any]:
    """The expected collections a source-only qualification determines (the contract generator's input): the target
    list, the frozen excluded games with their reasons, the parent witness digest, the counts and every key digest."""
    quals = qualified["qualifications"]
    targets: dict[str, dict[str, list[str]]] = {}
    for q in quals:
        targets.setdefault(str(q["season"]), {}).setdefault(q["contest_date"], []).append(q["contest_key"])
    for dates in targets.values():
        for keys in dates.values():
            keys.sort()
    excluded = {q["contest_key"]: list(q["support_reasons"]) for q in quals if q["support_state"] != "COMMON_SUPPORT"}
    witnesses = sorted(qualified["witnesses"], key=ca._score_order)
    expected = {"targets": {s: dict(sorted(d.items())) for s, d in sorted(targets.items())},
                "excluded_games": dict(sorted(excluded.items())),
                "parent_witness_lines_sha256": ca.lines_sha256([ca.canonical_line(w["parent_score"])
                                                                for w in witnesses])}
    keys = ca.expected_keys(expected)
    supported = [q for q in quals if q["support_state"] == "COMMON_SUPPORT"]
    expected["counts"] = {"targets": len(quals), "views": 2 * len(quals), "common_support_games": len(supported),
                          "excluded_games": len(excluded),
                          "fit_season_common_support_games": sum(1 for q in supported if q["season"] in ca.FIT_SEASONS),
                          "comparison_common_support_games": sum(1 for q in supported
                                                                 if q["season"] in ca.COMPARISON_SEASONS),
                          **{table: len(keys[table]) for table in ca.RECORD_TABLES}}
    expected["keys_sha256"] = {table: ca.keys_sha256(keys[table]) for table in ca.RECORD_TABLES}
    return expected


def check_expected(derived: dict[str, Any], anchors: dict[str, Any]) -> dict[str, Any]:
    """The derivation's key collections, frozen common cohort and parent witnesses must equal the contract's expected
    collections (observed by the source-only census before any fit); a difference is a refused population drift."""
    expected = anchors["expected"]
    keys = ca.expected_keys(expected)
    differing = [table for table in ca.RECORD_TABLES
                 if [ca.record_key(table, r) for r in derived[table]] != keys[table]]
    excluded = {q["contest_key"]: q["support_reasons"] for q in derived["qualifications"]
                if q["support_state"] != "COMMON_SUPPORT"}
    if excluded != expected["excluded_games"]:
        differing.append("excluded_games")
    if ca.lines_sha256([ca.canonical_line(w["parent_score"]) for w in derived["witnesses"]]) != \
            expected["parent_witness_lines_sha256"]:
        differing.append("parent_witness_lines_sha256")
    if differing:
        raise BuildRefused("CONTEXT_INPUT_POPULATION_DRIFT", f"the derivation differs from the contract's expected "
                                                             f"collections on {differing}")
    return {"tables_equal": list(ca.RECORD_TABLES), "excluded_games": len(excluded),
            "common_support_games": len(derived["qualifications"]) - len(excluded)}


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    """A hash-chained season checkpoint: each chunk of study seasons' record lines is written once (deterministic gzip)
    and its ledger row chains the prefix (the accepted C61 builder's checkpoint, unchanged but for the schema)."""

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
    """The record lines of every per-season block, through the target checkpoint when one is used (None when
    interrupted). The global parameter, summary and census blocks follow unchanged."""
    blocks = {(table, segment): list(lines) for table, segment, _records, lines in ca.block_lines(derived)}
    if checkpoint is None:
        return blocks
    done = checkpoint.completed(keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    index, written = len(done), 0
    while index * chunk_size < len(keys):
        index += 1
        start = (index - 1) * chunk_size
        chunk_keys = keys[start:start + chunk_size]
        blob = gzip.compress(ca.target_chunk(derived, chunk_keys), compresslevel=9, mtime=0)
        prefix = checkpoint.write_chunk(index, chunk_keys, blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(keys):
            return None
    rows = checkpoint.completed(keys)
    if sum(row["count"] for row in rows) != len(keys):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "the checkpoint does not cover every target")
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
    identity = sha256_bytes(ca.canonical_json_bytes(identity_document))
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
        with (temporary / ca.DB_FILE).open("xb") as handle:
            handle.write(data)
        if sha256_file(temporary / ca.DB_FILE) != declared[ca.DB_FILE]:
            raise BuildRefused("WRITE_VERIFY_FAILED", ca.DB_FILE)
        os.rename(temporary, target)
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        # canonical bytes, never Python equality (an integral float count equals its integer there)
        if existing.get("identity") != identity or \
                ca.canonical_json_bytes(existing.get("identity_document")) != ca.canonical_json_bytes(identity_document) \
                or ca.canonical_json_bytes(existing.get("content_document")) != ca.canonical_json_bytes(content_doc):
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


def fit_receipt(derived: dict[str, Any]) -> dict[str, Any]:
    """The two frozen fits as recorded in the parameter records (decimal12 and repr; never re-tuned)."""
    out = {}
    for record in derived["parameters"]:
        out[record["model_id"]] = {k: record[k] for k in ("parameter_state", "columns", "coefficients",
                                                          "coefficients_repr", "scales", "scales_repr",
                                                          "constant_columns", "convergence")}
        out[record["model_id"]]["training_games"] = (record["training"] or {}).get("games")
    return out


def primary_comparison(derived: dict[str, Any]) -> dict[str, Any] | None:
    return next((r for r in derived["summary"] if r["primary"]), None)


def build(args: argparse.Namespace, loader: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha, anchors = load_contract(args.contract, args.repo_root)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    load = loader or load_inputs
    try:
        inputs = load(args.data_root, anchors, input_order=args.input_order)
        derived = derive(inputs, anchors)
    except ca.ContextError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    except rf.ReferenceFitError as exc:  # never expected: derive records fit failures; kept explicit, never masked
        raise BuildRefused(f"CONTEXT_{exc.code}", str(exc)) from exc
    expectation = check_expected(derived, anchors)
    keys = [q["contest_key"] for q in derived["qualifications"]]
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "inputs_sha256": {n: spec["sha256"] for n, spec in _input_specs(anchors)},
                  "payload_schema": ca.PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                  "target_list_sha256": _keys_sha(keys), "target_count": len(keys),
                  "producer_sha256": sha256_file(Path(__file__)), "module_sha256": sha256_file(Path(ca.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = build_lines(derived, keys, chunk_size=args.chunk_size, checkpoint=checkpoint,
                        stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0,
                "target_count": len(keys)}
    if built != {(t, s): list(lines) for t, s, _r, lines in ca.block_lines(derived)}:
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    document = ca.content_document(anchors, derived)
    content_identity = sha256_bytes(ca.canonical_json_bytes(document))
    meta = ca.meta_values(anchors, content_identity, derived)
    work_parent = Path(args.work_root) if args.work_root else None
    with tempfile.TemporaryDirectory(prefix="scs-", dir=work_parent) as work:
        db_path = Path(work) / ca.DB_FILE
        table_counts = ca.build_database(db_path, derived, meta)
        database_doc = ca.database_document(contract_sha, content_identity, sha256_file(db_path), table_counts)
        database_identity = sha256_bytes(ca.canonical_json_bytes(database_doc))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "module_path": str(Path(ca.__file__).resolve()),
                      "module_sha256": sha256_file(Path(ca.__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                      "chunk_size": args.chunk_size, "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "data_root": str(args.data_root), "content_identity": content_identity,
                      "database_identity": database_identity}
        result = materialize(args.output_root, args.manifest_root, database_doc, db_path, content_identity, document,
                             provenance)
    materialized_db = Path(result["data_dir"]) / ca.DB_FILE
    try:
        with ca.ContextAssociation(materialized_db, manifest=Path(result["manifest"]),
                                   anchors={**anchors, "profile": None}) as reader:
            reader_check = {"verified": True, "identity": reader.database_identity,
                            "content_identity": reader.content_identity, "refit_rederived": True}
    except ca.ContextError as exc:
        raise BuildRefused("MATERIALIZED_RELEASE_REFUSED_BY_READER", str(exc)) from exc
    production = {k: ca.ANCHORS.get(k) for k in ANCHOR_KEYS}
    profile = ca.CONTEXT_PROFILE
    return {"state": result["state"], "content_identity": content_identity, "database_identity": database_identity,
            "release": result, "reader_check": reader_check, "expected_collections": expectation,
            "census": derived["census"][0]["population"], "primary_comparison": primary_comparison(derived),
            "fits": fit_receipt(derived), "row_counts": document["row_counts"], "table_counts": table_counts,
            "database_sha256": database_doc["outputs"][ca.DB_FILE], "database_bytes": materialized_db.stat().st_size,
            "lines_sha256": document["lines_sha256"], "summary_sha256": meta["summary_sha256"],
            "census_sha256": meta["census_sha256"], "rules_sha256": ca.rules_sha256(), "contract_sha256": contract_sha,
            "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: anchors[k] for k in ANCHOR_KEYS} == production,
            "contract_pinned_by_reader": contract_sha == ca.ANCHORS.get("contract_sha256"),
            "profile_pinned": profile,
            "profile_reproduced": profile is not None and
            (profile.get("content_identity"), profile.get("database_identity")) == (content_identity, database_identity),
            "inputs": {n: {"sha256": spec["sha256"], "path": str((inputs.get("paths") or {}).get(n))}
                       for n, spec in _input_specs(anchors)},
            "input_order": args.input_order, "chunk_size": args.chunk_size, "resumed": bool(args.resume),
            "variant": args.variant, "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser(repo_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_site_calendar_association", allow_abbrev=False,
                                     description="Build the national retrospective site/calendar association release "
                                                 "2016-2023.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path,
                        help="the data root holding every pinned input at the contract's relative locators")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=repo_root,
                        help="the checkout whose parent contracts the contract pins (default: this checkout)")
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
         repo_root: Path | None = None, program: str = "tools/cycle63/build_national_site_calendar_association.py"
         ) -> int:
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
