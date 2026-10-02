r"""Build the national 2016-2023 FBS retrospective history-prefix dataset (BAT-711, Cycle #39 TP39-A01).

``python -B tools/build_national_history_prefix.py --contract configs/national_history_prefix_2016_2023_contract.json
--parent-database <data>/canonical/national_di_population_2016_2025/sha256/<id>/national_population.sqlite
--output-root <data>/canonical/national_history_prefix_2016_2023
--manifest-root <data>/manifests/national_history_prefix_2016_2023``

Standard library only. The producer verifies the bound parent (file hash, manifest identity, contract hash, schema,
contest/program-season identities) before reading any row, reads only ``contest_key`` and ``season`` for parent rows
outside 2016-2023, and writes:

* ``targets.jsonl`` -- every 2016-2023 FBS_ESTIMAND_SUBSET contest passing every contract predicate;
* ``history.jsonl`` -- exactly two views (A, B) per target with same-season, strictly-earlier-date team and
  current-opponent histories: contributing contests with lineage, integer totals and unreduced rational rates;
* ``exclusions.jsonl`` -- every other 2016-2023 parent contest with its exact reasons and pool membership;
* ``labels.jsonl`` -- the target outcomes, physically separate from every history record;
* ``out_of_scope.jsonl`` -- parent contests outside 2016-2023 (key and season only);
* ``national_history.sqlite`` -- the deterministic read-only query database over those payloads.

Every row is RETROSPECTIVE_OBSERVATION_ONLY / PIT_ELIGIBILITY_NOT_ESTABLISHED: calendar order is not publication or
availability time. Outputs are create-only and content addressed; nothing is overwritten. ``--chunk-size`` with
``--checkpoint-dir`` builds through a hash-chained checkpoint that ``--resume`` verifies (contract, parent, schema,
producer, census and exact key prefix); ``--stop-after-chunks`` simulates an interruption.
"""
from __future__ import annotations

import argparse
import bisect
import datetime as _dt
import hashlib
import json
import os
import platform
import random
import re
import sqlite3
import sys
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any, Iterable, Sequence

PRODUCER = "national_history_prefix/1.0.0"
POPULATION = "national_history_prefix_2016_2023"
CONTRACT_SCHEMA = "1.0.0"
CONTRACT_ID_PREFIX = "BAT-711-NATIONAL-HISTORY-PREFIX-2016-2023-"
PAYLOAD_SCHEMA = "BAS-NATIONAL-HISTORY-PREFIX-PAYLOAD-1"
CONTENT_SCHEMA = "BAS-NATIONAL-HISTORY-PREFIX-CONTENT-1"
DATABASE_SCHEMA = "BAS-NATIONAL-HISTORY-PREFIX-DATABASE-1"
DB_SCHEMA = "BAS-NATIONAL-HISTORY-PREFIX-DB-1"
CHECKPOINT_SCHEMA = "BAS-NATIONAL-HISTORY-PREFIX-CHECKPOINT-1"
PARENT_DB_FILE = "national_population.sqlite"
PARENT_DB_SCHEMA = "BAS-NATIONAL-DI-POPULATION-DB-1"
PARENT_POPULATION = "national_di_population_2016_2025"
DB_FILE = "national_history.sqlite"
SUBSET = "FBS_ESTIMAND_SUBSET"
TARGET_SEASONS = tuple(range(2016, 2024))
PROTECTED_SEASONS = (2024, 2025)
PROSPECTIVE_SEASONS = (2026,)
ROW_LABELS = {"observation_authority": "RETROSPECTIVE_OBSERVATION_ONLY",
              "pit_eligibility": "PIT_ELIGIBILITY_NOT_ESTABLISHED",
              "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME"}
PRIOR_RULE = "SAME_SEASON_DATE_STRICTLY_BEFORE_TARGET_DATE"
PAYLOAD_FILES = ("targets.jsonl", "history.jsonl", "exclusions.jsonl", "labels.jsonl", "out_of_scope.jsonl")
ORG_KEY = re.compile(r"^org:([0-9]+)$")
ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
INPUT_ORDER = re.compile(r"^(natural|reverse|shuffle:[0-9]{1,9})$")
INTERRUPTED_EXIT = 3

PARENT_COLUMNS = ("contest_key", "ncaa_contest_id", "season", "term", "contest_date", "site", "neutral_site_text",
                  "contest_status", "competitive", "a_org_id", "a_team_season_id", "a_team_name", "a_division_label",
                  "a_points", "b_org_id", "b_team_season_id", "b_team_name", "b_division_label", "b_points",
                  "classification_pair", "source", "cfbd_game_ids", "reconciliation_state", "disposition",
                  "a_key", "b_key", "contest_dates_observed")

#: Closed record schemas (contract payloads.serialization.closed_schema and record_fields).
RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    "target": ("record_type", "contest_key", "ncaa_contest_id", "season", "term", "contest_date", "a_key", "b_key",
               "a_org_id", "b_org_id", "a_team_name", "b_team_name", "a_team_season_id", "b_team_season_id",
               "a_division_label", "b_division_label", "classification_pair", "parent_site", "neutral_site_text",
               "source", "cfbd_game_ids", "parent_disposition", "parent_reconciliation_state", "views",
               *ROW_LABELS),
    "history_view": ("record_type", "target_contest_key", "view", "season", "term", "target_date", "prior_rule",
                     "team_key", "team_org_id", "team_name", "team_division_label", "opponent_key",
                     "opponent_org_id", "opponent_name", "opponent_division_label", "team_history",
                     "opponent_history", *ROW_LABELS),
    "history_block": ("team_key", "season", "history_state", "games", "wins", "losses", "ties", "points_for_total",
                      "points_against_total", "margin_total", "rate_denominator", "win_rate", "points_for_mean",
                      "points_against_mean", "margin_mean", "contributing_contest_keys", "contributing",
                      "excluded_inputs"),
    "contributing": ("contest_key", "contest_date", "side", "opponent_key", "opponent_division_label",
                     "points_for", "points_against", "result"),
    "excluded_input": ("contest_key", "contest_date", "opponent_key", "reasons"),
    "rate": ("numerator", "denominator"),
    "exclusion": ("record_type", "contest_key", "ncaa_contest_id", "season", "term", "contest_date", "a_key",
                  "b_key", "a_team_name", "b_team_name", "classification_pair", "fbs_estimand_subset",
                  "target_exclusion_reasons", "history_pool_member", "history_pool_exclusion_reasons",
                  "parent_disposition", "parent_reconciliation_state", "parent_contest_status",
                  "parent_competitive", "score_state", *ROW_LABELS),
    "target_label": ("record_type", "contest_key", "season", "contest_date", "a_key", "b_key", "a_points",
                     "b_points", "a_margin", "a_result", "b_result", "label_authority", *ROW_LABELS),
    "out_of_scope": ("record_type", "contest_key", "season", "reason", *ROW_LABELS),
}


class BuildRefused(Exception):
    """A refused build; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --------------------------------------------------------------------------------------------- serialization

def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _check_fields(kind: str, value: dict[str, Any]) -> None:
    expected = RECORD_FIELDS[kind]
    if set(value) != set(expected):
        raise BuildRefused("UNKNOWN_FIELD", f"{kind} fields {sorted(set(value) ^ set(expected))}")


def record_line(record: dict[str, Any]) -> bytes:
    _check_fields(record["record_type"], record)
    if record["record_type"] == "history_view":
        for block in (record["team_history"], record["opponent_history"]):
            _check_fields("history_block", block)
            for item in block["contributing"]:
                _check_fields("contributing", item)
            for item in block["excluded_inputs"]:
                _check_fields("excluded_input", item)
            for name in ("win_rate", "points_for_mean", "points_against_mean", "margin_mean"):
                if block[name] is not None:
                    _check_fields("rate", block[name])
    _assert_no_float(record)
    return canonical_json_bytes(record) + b"\n"


def _assert_no_float(value: Any) -> None:
    if isinstance(value, float):
        raise BuildRefused("FLOAT_IN_PAYLOAD", repr(value))
    if isinstance(value, dict):
        for item in value.values():
            _assert_no_float(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_float(item)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------------------------- contract

def load_contract(path: Path) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    try:
        contract = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("CONTRACT_INVALID", str(exc)) from exc
    if contract.get("schema_version") != CONTRACT_SCHEMA or not str(contract.get("contract_id", "")).startswith(
            CONTRACT_ID_PREFIX):
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN",
                           f"schema {contract.get('schema_version')!r} id {contract.get('contract_id')!r}")
    authority = contract.get("authority") or {}
    for key, value in ROW_LABELS.items():
        if authority.get(key) != value:
            raise BuildRefused("FORGED_PIT_AUTHORITY", f"authority.{key} is {authority.get(key)!r}, not {value!r}")
    labels = (contract.get("payloads") or {}).get("row_labels")
    if labels != ROW_LABELS:
        raise BuildRefused("FORGED_PIT_AUTHORITY", f"payloads.row_labels is {labels!r}")
    if authority.get("require_pit") != "REFUSED_PIT_ELIGIBILITY_NOT_ESTABLISHED":
        raise BuildRefused("FORGED_PIT_AUTHORITY", "require_pit must be refused")
    scope = contract.get("scope") or {}
    seasons = scope.get("target_seasons")
    if seasons != list(TARGET_SEASONS):
        bad = sorted(set(seasons or []) & set(PROTECTED_SEASONS + PROSPECTIVE_SEASONS))
        raise BuildRefused("PROTECTED_SEASON_IN_SCOPE" if bad else "CONTRACT_INVALID",
                           f"target seasons {seasons!r}; protected/prospective present: {bad}")
    if scope.get("protected_seasons") != list(PROTECTED_SEASONS) or scope.get("target_subset") != SUBSET:
        raise BuildRefused("CONTRACT_INVALID", "protected seasons or target subset differ")
    if (contract.get("payloads") or {}).get("schema_version") != PAYLOAD_SCHEMA:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "payload schema differs")
    declared = (contract.get("payloads") or {}).get("record_fields")
    if declared != {k: list(v) for k, v in RECORD_FIELDS.items()}:
        raise BuildRefused("CONTRACT_INVALID", "payloads.record_fields differ from the producer's closed schemas")
    binding = contract.get("parent_binding") or {}
    for key in ("query_db_identity", "sqlite_sha256", "contract_sha256", "contest_identity",
                "program_season_identity", "schema_version"):
        if not isinstance(binding.get(key), str) or not binding[key]:
            raise BuildRefused("CONTRACT_INVALID", f"parent_binding.{key} missing")
    return contract, sha256_bytes(raw)


# --------------------------------------------------------------------------------------------- parent

def parent_manifest_for(database: Path) -> Path:
    db = Path(database).resolve()
    population_root = db.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / db.parent.name / \
        "run_manifest.json"


def verify_parent(contract: dict[str, Any], database: Path, manifest: Path | None) -> dict[str, Any]:
    binding = contract["parent_binding"]
    db = Path(database)
    if not db.is_file() or db.name != PARENT_DB_FILE or db.resolve().parent.name != binding["query_db_identity"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"{db} is not <root>/sha256/{binding['query_db_identity']}/"
                           + PARENT_DB_FILE)
    actual = sha256_file(db)
    if actual != binding["sqlite_sha256"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"parent database hashes to {actual}")
    manifest_path = Path(manifest) if manifest is not None else parent_manifest_for(db)
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity_document = document["identity_document"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"parent manifest unreadable: {exc}") from exc
    computed = sha256_bytes(canonical_json_bytes(identity_document))
    upstream = identity_document.get("upstream") or {}
    checks = {"identity": computed == binding["query_db_identity"] == document.get("identity"),
              "stage": identity_document.get("stage") == "query-db",
              "outputs": (identity_document.get("outputs") or {}).get(PARENT_DB_FILE) == actual,
              "contract": identity_document.get("contract_sha256") == binding["contract_sha256"],
              "contest": upstream.get("contest") == binding["contest_identity"],
              "program_season": upstream.get("program-season") == binding["program_season_identity"]}
    if not all(checks.values()):
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"parent manifest checks {checks}")
    return {"query_db_identity": computed, "sqlite_sha256": actual, "manifest": str(manifest_path),
            "contract_sha256": binding["contract_sha256"], "contest_identity": binding["contest_identity"],
            "program_season_identity": binding["program_season_identity"]}


def read_parent(contract: dict[str, Any], database: Path) -> dict[str, Any]:
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
        binding = contract["parent_binding"]
        if meta.get("schema_version") != binding["schema_version"] or meta.get("schema_version") != PARENT_DB_SCHEMA:
            raise BuildRefused("PARENT_SCHEMA_UNKNOWN", f"parent schema {meta.get('schema_version')!r}")
        if (meta.get("contract_sha256"), meta.get("contest_identity"), meta.get("program_season_identity")) != (
                binding["contract_sha256"], binding["contest_identity"], binding["program_season_identity"]):
            raise BuildRefused("PARENT_BINDING_MISMATCH", "parent meta identities differ from the binding")
        bad_types = conn.execute("SELECT COUNT(*) FROM contest WHERE typeof(season) != 'integer' "
                                 "OR typeof(contest_key) != 'text'").fetchone()[0]
        if bad_types:
            raise BuildRefused("PARENT_SCHEMA_INVALID", f"{bad_types} parent rows have a non-integer season or key")
        census = [(row["contest_key"], row["season"]) for row in
                  conn.execute("SELECT contest_key, season FROM contest ORDER BY rowid")]
        columns = ", ".join(PARENT_COLUMNS)
        rows = [dict(row) for row in conn.execute(
            f"SELECT {columns} FROM contest WHERE season >= ? AND season <= ? ORDER BY rowid",
            (TARGET_SEASONS[0], TARGET_SEASONS[-1]))]
        subset_rows = [row[0] for row in conn.execute(
            "SELECT contest_key FROM subset_membership WHERE subset = ? ORDER BY rowid", (SUBSET,))]
    finally:
        conn.close()
    keys = [key for key, _season in census]
    if len(set(keys)) != len(keys):
        raise BuildRefused("PARENT_DUPLICATE_KEY", f"{len(keys) - len(set(keys))} duplicate parent contest keys")
    if len(set(subset_rows)) != len(subset_rows):
        raise BuildRefused("PARENT_DUPLICATE_KEY", "duplicate FBS_ESTIMAND_SUBSET membership rows")
    unknown = sorted(set(subset_rows) - set(keys))
    if unknown:
        raise BuildRefused("SUBSET_KEY_UNKNOWN", f"subset keys absent from the parent: {unknown[:5]}")
    return {"census": census, "rows": rows, "subset": set(subset_rows), "meta": meta}


# --------------------------------------------------------------------------------------------- predicates

def valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not ISO_DATE.match(value):
        return False
    try:
        return _dt.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def pool_reasons(row: dict[str, Any]) -> list[str]:
    """Every failing contract predicate for one 2016-2023 parent contest, in contract order."""
    reasons: list[str] = []
    if row["disposition"] != "VERIFIED_PRESENT":
        reasons.append("DISPOSITION_NOT_VERIFIED_PRESENT")
    if row["reconciliation_state"] != "RECONCILED_2016_2023":
        reasons.append("RECONCILIATION_NOT_RECONCILED_2016_2023")
    if row["contest_status"] != "COMPLETED":
        reasons.append("STATUS_NOT_COMPLETED")
    if not (type(row["competitive"]) is int and row["competitive"] == 1):
        reasons.append("NOT_COMPETITIVE")
    if not valid_date(row["contest_date"]):
        reasons.append("DATE_INVALID")
    else:
        observed = row.get("contest_dates_observed")
        if observed is not None:
            try:
                dates = json.loads(observed) if isinstance(observed, str) else observed
            except ValueError:
                dates = None
            if not isinstance(dates, list) or set(dates) != {row["contest_date"]}:
                reasons.append("DATE_NOT_SINGLE")
    stable = True
    for side in ("a", "b"):
        match = ORG_KEY.match(row[f"{side}_key"] or "") if isinstance(row[f"{side}_key"], str) else None
        if not match or match.group(1) != str(row[f"{side}_org_id"]):
            stable = False
    if not stable:
        reasons.append("ORG_KEY_NOT_STABLE")
    if row["a_key"] == row["b_key"]:
        reasons.append("ORG_KEYS_NOT_DISTINCT")
    points = (row["a_points"], row["b_points"])
    if any(p is None for p in points):
        reasons.append("SCORE_MISSING")
    if any(p is not None and not (type(p) is int and p >= 0) for p in points):
        reasons.append("SCORE_NOT_NONNEGATIVE_INTEGER")
    return reasons


def score_state(row: dict[str, Any]) -> str:
    points = (row["a_points"], row["b_points"])
    if any(p is None for p in points):
        return "MISSING"
    return "NONNEGATIVE_INTEGERS" if all(type(p) is int and p >= 0 for p in points) else "INVALID"


def _json_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except ValueError:
        return [value]
    return parsed if isinstance(parsed, list) else [parsed]


# --------------------------------------------------------------------------------------------- dataset

def permute(rows: list[dict[str, Any]], order: str) -> list[dict[str, Any]]:
    if not INPUT_ORDER.match(order):
        raise BuildRefused("INPUT_ORDER_INVALID", order)
    rows = list(rows)
    if order == "reverse":
        rows.reverse()
    elif order.startswith("shuffle:"):
        random.Random(int(order.split(":", 1)[1])).shuffle(rows)
    return rows


class Dataset:
    """Indexes for one bound parent; every output record is derived from these immutable inputs."""

    def __init__(self, parent: dict[str, Any], input_order: str = "natural") -> None:
        rows = permute(parent["rows"], input_order)
        subset = parent["subset"]
        self.census = sorted(parent["census"], key=lambda item: (item[1], item[0]))
        self.targets: list[dict[str, Any]] = []
        self.exclusions: list[dict[str, Any]] = []
        self.pool: dict[tuple[int, str], list[tuple[str, str, dict[str, Any]]]] = {}
        self.excluded: dict[tuple[int, str], list[tuple[str, str, dict[str, Any], list[str]]]] = {}
        inconsistent = []
        for row in rows:
            in_subset = row["contest_key"] in subset
            both_fbs = row["a_division_label"] == "FBS" and row["b_division_label"] == "FBS"
            if in_subset != both_fbs:
                inconsistent.append(row["contest_key"])
            reasons = pool_reasons(row)
            if not reasons:
                for side in ("a", "b"):
                    self.pool.setdefault((row["season"], row[f"{side}_key"]), []).append(
                        (row["contest_date"], row["contest_key"], row))
            else:
                for side in ("a", "b"):
                    if isinstance(row[f"{side}_key"], str):
                        date = row["contest_date"] if valid_date(row["contest_date"]) else ""
                        self.excluded.setdefault((row["season"], row[f"{side}_key"]), []).append(
                            (date, row["contest_key"], row, reasons))
            if in_subset and not reasons:
                self.targets.append(row)
            else:
                target_reasons = ([] if in_subset else ["NOT_IN_FBS_ESTIMAND_SUBSET"]) + reasons
                self.exclusions.append(self._exclusion(row, in_subset, target_reasons, reasons))
        if inconsistent:
            raise BuildRefused("SUBSET_FIELD_INCONSISTENT",
                               f"{len(inconsistent)} contests disagree with both-FBS labels: {sorted(inconsistent)[:5]}")
        for entries in self.pool.values():
            entries.sort(key=lambda item: (item[0], item[1]))
        for entries in self.excluded.values():
            entries.sort(key=lambda item: (item[0], item[1]))
        self.pool_dates = {key: [item[0] for item in entries] for key, entries in self.pool.items()}
        self.targets.sort(key=lambda row: (row["season"], row["contest_date"], row["contest_key"]))
        self.exclusions.sort(key=lambda rec: (rec["season"], rec["contest_date"] or "", rec["contest_key"]))
        in_scope = {row["contest_key"] for row in rows}
        self.out_of_scope = [self._out_of_scope(key, season) for key, season in self.census
                             if season not in TARGET_SEASONS]
        if len(in_scope) != sum(1 for _key, season in self.census if season in TARGET_SEASONS):
            raise BuildRefused("CENSUS_INCOMPLETE", "2016-2023 parent rows and census disagree")
        self.target_keys = [row["contest_key"] for row in self.targets]

    @staticmethod
    def _exclusion(row: dict[str, Any], in_subset: bool, target_reasons: list[str],
                   reasons: list[str]) -> dict[str, Any]:
        return {"record_type": "exclusion", "contest_key": row["contest_key"],
                "ncaa_contest_id": row["ncaa_contest_id"], "season": row["season"], "term": row["term"],
                "contest_date": row["contest_date"], "a_key": row["a_key"], "b_key": row["b_key"],
                "a_team_name": row["a_team_name"], "b_team_name": row["b_team_name"],
                "classification_pair": row["classification_pair"], "fbs_estimand_subset": in_subset,
                "target_exclusion_reasons": target_reasons, "history_pool_member": not reasons,
                "history_pool_exclusion_reasons": reasons, "parent_disposition": row["disposition"],
                "parent_reconciliation_state": row["reconciliation_state"],
                "parent_contest_status": row["contest_status"], "parent_competitive": row["competitive"],
                "score_state": score_state(row), **ROW_LABELS}

    @staticmethod
    def _out_of_scope(key: str, season: int) -> dict[str, Any]:
        reason = ("PROTECTED_EXPOSED_SEASON_2024_2025" if season in PROTECTED_SEASONS
                  else "SEASON_OUTSIDE_2016_2023")
        return {"record_type": "out_of_scope", "contest_key": key, "season": season, "reason": reason, **ROW_LABELS}

    # ------------------------------------------------------------------ histories

    def history_block(self, team_key: str, season: int, target_date: str, target_key: str) -> dict[str, Any]:
        entries = self.pool.get((season, team_key), [])
        dates = self.pool_dates.get((season, team_key), [])
        cut = bisect.bisect_left(dates, target_date)
        contributing = []
        totals = {"games": 0, "wins": 0, "losses": 0, "ties": 0, "points_for_total": 0, "points_against_total": 0}
        for date, key, row in entries[:cut]:
            side = "a" if row["a_key"] == team_key else "b"
            other = "b" if side == "a" else "a"
            pf, pa = row[f"{side}_points"], row[f"{other}_points"]
            result = "W" if pf > pa else ("L" if pf < pa else "T")
            contributing.append({"contest_key": key, "contest_date": date, "side": side.upper(),
                                 "opponent_key": row[f"{other}_key"],
                                 "opponent_division_label": row[f"{other}_division_label"], "points_for": pf,
                                 "points_against": pa, "result": result})
            totals["games"] += 1
            totals["wins" if result == "W" else ("losses" if result == "L" else "ties")] += 1
            totals["points_for_total"] += pf
            totals["points_against_total"] += pa
        excluded = []
        for date, key, row in entries[cut:]:
            if date != target_date:
                break
            if key != target_key:
                excluded.append({"contest_key": key, "contest_date": date,
                                 "opponent_key": row["b_key"] if row["a_key"] == team_key else row["a_key"],
                                 "reasons": ["SAME_DATE_NOT_STRICTLY_EARLIER"]})
        for date, key, row, reasons in self.excluded.get((season, team_key), []):
            if date and date > target_date:
                continue
            extra = ["SAME_DATE_NOT_STRICTLY_EARLIER"] if date == target_date else []
            excluded.append({"contest_key": key, "contest_date": row["contest_date"],
                             "opponent_key": row["b_key"] if row["a_key"] == team_key else row["a_key"],
                             "reasons": reasons + extra})
        excluded.sort(key=lambda item: (item["contest_date"] if valid_date(item["contest_date"]) else "",
                                        item["contest_key"]))
        games = totals["games"]
        margin = totals["points_for_total"] - totals["points_against_total"]

        def rate(numerator: int) -> dict[str, int] | None:
            return {"numerator": numerator, "denominator": games} if games else None
        return {"team_key": team_key, "season": season,
                "history_state": "HAS_PRIOR_CONTESTS" if games else "COLD_START", **totals,
                "margin_total": margin, "rate_denominator": games, "win_rate": rate(totals["wins"]),
                "points_for_mean": rate(totals["points_for_total"]),
                "points_against_mean": rate(totals["points_against_total"]), "margin_mean": rate(margin),
                "contributing_contest_keys": [item["contest_key"] for item in contributing],
                "contributing": contributing, "excluded_inputs": excluded}

    def bundle(self, row: dict[str, Any]) -> bytes:
        """Four canonical lines for one target: target, history A, history B, label."""
        key, season, date = row["contest_key"], row["season"], row["contest_date"]
        target = {"record_type": "target", "contest_key": key, "ncaa_contest_id": row["ncaa_contest_id"],
                  "season": season, "term": row["term"], "contest_date": date, "a_key": row["a_key"],
                  "b_key": row["b_key"], "a_org_id": row["a_org_id"], "b_org_id": row["b_org_id"],
                  "a_team_name": row["a_team_name"], "b_team_name": row["b_team_name"],
                  "a_team_season_id": row["a_team_season_id"], "b_team_season_id": row["b_team_season_id"],
                  "a_division_label": row["a_division_label"], "b_division_label": row["b_division_label"],
                  "classification_pair": row["classification_pair"], "parent_site": row["site"],
                  "neutral_site_text": row["neutral_site_text"], "source": row["source"],
                  "cfbd_game_ids": _json_list(row["cfbd_game_ids"]), "parent_disposition": row["disposition"],
                  "parent_reconciliation_state": row["reconciliation_state"], "views": ["A", "B"], **ROW_LABELS}
        lines = [record_line(target)]
        for view, side, other in (("A", "a", "b"), ("B", "b", "a")):
            history = {"record_type": "history_view", "target_contest_key": key, "view": view, "season": season,
                       "term": row["term"], "target_date": date, "prior_rule": PRIOR_RULE,
                       "team_key": row[f"{side}_key"], "team_org_id": row[f"{side}_org_id"],
                       "team_name": row[f"{side}_team_name"], "team_division_label": row[f"{side}_division_label"],
                       "opponent_key": row[f"{other}_key"], "opponent_org_id": row[f"{other}_org_id"],
                       "opponent_name": row[f"{other}_team_name"],
                       "opponent_division_label": row[f"{other}_division_label"],
                       "team_history": self.history_block(row[f"{side}_key"], season, date, key),
                       "opponent_history": self.history_block(row[f"{other}_key"], season, date, key),
                       **ROW_LABELS}
            lines.append(record_line(history))
        a, b = row["a_points"], row["b_points"]
        label = {"record_type": "target_label", "contest_key": key, "season": season, "contest_date": date,
                 "a_key": row["a_key"], "b_key": row["b_key"], "a_points": a, "b_points": b, "a_margin": a - b,
                 "a_result": "W" if a > b else ("L" if a < b else "T"),
                 "b_result": "W" if b > a else ("L" if b < a else "T"),
                 "label_authority": "POSTGAME_OUTCOME_SEPARATED_FROM_HISTORY", **ROW_LABELS}
        lines.append(record_line(label))
        return b"".join(lines)

    def census_bytes(self) -> tuple[bytes, bytes]:
        return (b"".join(record_line(rec) for rec in self.exclusions),
                b"".join(record_line(rec) for rec in self.out_of_scope))


def split_bundles(blob: bytes) -> dict[str, bytes]:
    lines = blob.splitlines(keepends=True)
    if len(lines) % 4:
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "bundle stream is not a multiple of four records")
    return {"targets.jsonl": b"".join(lines[0::4]),
            "history.jsonl": b"".join(line for pair in zip(lines[1::4], lines[2::4]) for line in pair),
            "labels.jsonl": b"".join(lines[3::4])}


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    def __init__(self, directory: Path, header: dict[str, Any], chunk_size: int, resume: bool) -> None:
        self.dir = Path(directory)
        self.header = header
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
        return self.dir / "chunks" / f"chunk_{index:06d}.jsonl"

    def completed(self, target_keys: list[str]) -> list[dict[str, Any]]:
        """Verify the ledger, every chunk file and the chained key prefix; return the completed chunk rows."""
        if not self.ledger.is_file():
            return []
        text = self.ledger.read_text(encoding="utf-8")
        lines = text.split("\n")
        rows = [json.loads(line) for line in lines[:-1] if line]  # a torn, unterminated last line is not complete
        prefix = ""
        for expected_index, row in enumerate(rows, start=1):
            start = (expected_index - 1) * self.chunk_size
            keys = target_keys[start:start + self.chunk_size]
            path = self.chunk_path(expected_index)
            if row.get("index") != expected_index or row.get("count") != len(keys) or \
                    row.get("keys_sha256") != _keys_sha(keys) or not keys or \
                    row.get("first_key") != keys[0] or row.get("last_key") != keys[-1]:
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


def build_bundles(dataset: Dataset, *, chunk_size: int, checkpoint: Checkpoint | None,
                  stop_after: int | None) -> bytes | None:
    targets = dataset.targets
    if checkpoint is None:
        return b"".join(dataset.bundle(row) for row in targets)
    size = chunk_size
    done = checkpoint.completed(dataset.target_keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    written = 0
    index = len(done)
    while index * size < len(targets):
        index += 1
        rows = targets[(index - 1) * size:index * size]
        blob = b"".join(dataset.bundle(row) for row in rows)
        prefix = checkpoint.write_chunk(index, [row["contest_key"] for row in rows], blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * size < len(targets):
            return None
    rows = checkpoint.completed(dataset.target_keys)
    if sum(row["count"] for row in rows) != len(targets):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpoint does not cover every target")
    return b"".join(checkpoint.chunk_path(row["index"]).read_bytes() for row in rows)


# --------------------------------------------------------------------------------------------- database

def build_database(path: Path, payloads: dict[str, bytes], meta: dict[str, str]) -> dict[str, int]:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        conn.executescript(
            "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "CREATE TABLE targets (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL UNIQUE, season INTEGER NOT NULL,"
            " contest_date TEXT NOT NULL, a_key TEXT NOT NULL, b_key TEXT NOT NULL, record TEXT NOT NULL);"
            "CREATE TABLE history (ord INTEGER PRIMARY KEY, target_contest_key TEXT NOT NULL, view TEXT NOT NULL,"
            " season INTEGER NOT NULL, target_date TEXT NOT NULL, team_key TEXT NOT NULL, opponent_key TEXT NOT NULL,"
            " record TEXT NOT NULL, UNIQUE (target_contest_key, view));"
            "CREATE TABLE exclusions (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL UNIQUE,"
            " season INTEGER NOT NULL, contest_date TEXT, a_key TEXT, b_key TEXT, record TEXT NOT NULL);"
            "CREATE TABLE target_labels (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL UNIQUE,"
            " record TEXT NOT NULL);")
        conn.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))

        def records(name: str) -> Iterable[tuple[int, dict[str, Any], str]]:
            for index, line in enumerate(payloads[name].decode("utf-8").splitlines()):
                yield index, json.loads(line), line
        conn.executemany("INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [(i, r["contest_key"], r["season"], r["contest_date"], r["a_key"], r["b_key"], line)
                          for i, r, line in records("targets.jsonl")])
        conn.executemany("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         [(i, r["target_contest_key"], r["view"], r["season"], r["target_date"], r["team_key"],
                           r["opponent_key"], line) for i, r, line in records("history.jsonl")])
        conn.executemany("INSERT INTO exclusions VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [(i, r["contest_key"], r["season"], r["contest_date"], r["a_key"], r["b_key"], line)
                          for i, r, line in records("exclusions.jsonl")])
        conn.executemany("INSERT INTO target_labels VALUES (?, ?, ?)",
                         [(i, r["contest_key"], line) for i, r, line in records("labels.jsonl")])
        conn.executescript(
            "CREATE INDEX ix_targets_season ON targets (season, ord);"
            "CREATE INDEX ix_targets_a ON targets (a_key, ord);"
            "CREATE INDEX ix_targets_b ON targets (b_key, ord);"
            "CREATE INDEX ix_history_team ON history (team_key, ord);"
            "CREATE INDEX ix_history_season ON history (season, ord);"
            "CREATE INDEX ix_exclusions_season ON exclusions (season, ord);"
            "CREATE INDEX ix_exclusions_a ON exclusions (a_key, ord);"
            "CREATE INDEX ix_exclusions_b ON exclusions (b_key, ord);")
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for table in ("meta", "targets", "history", "exclusions", "target_labels")}
    finally:
        conn.close()
    return counts


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any],
                files: dict[str, Path | bytes], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = sha256_bytes(canonical_json_bytes(identity_document))
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
        for name, source in files.items():
            data = source if isinstance(source, bytes) else Path(source).read_bytes()
            with (temporary / name).open("xb") as handle:
                handle.write(data)
            if sha256_file(temporary / name) != declared[name]:
                raise BuildRefused("WRITE_VERIFY_FAILED", name)
        os.rename(temporary, target)
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        if existing.get("identity") != identity or existing.get("identity_document") != identity_document:
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"{manifest} names a different identity")
        manifest_state = "ALREADY_PRESENT"
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"identity": identity, "identity_document": identity_document,
                                     "provenance": provenance}, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        manifest_state = "WRITTEN"
    return {"identity": identity, "state": state, "data_dir": str(target), "manifest": str(manifest),
            "manifest_state": manifest_state}


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha = load_contract(args.contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    parent_binding = verify_parent(contract, args.parent_database, args.parent_manifest)
    parent = read_parent(contract, args.parent_database)
    dataset = Dataset(parent, args.input_order)
    exclusions_bytes, out_of_scope_bytes = dataset.census_bytes()
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "parent_query_db_identity": parent_binding["query_db_identity"],
                  "parent_sqlite_sha256": parent_binding["sqlite_sha256"], "payload_schema": PAYLOAD_SCHEMA,
                  "chunk_size": args.chunk_size, "target_key_list_sha256": _keys_sha(dataset.target_keys),
                  "target_count": len(dataset.target_keys),
                  "census_sha256": sha256_bytes(exclusions_bytes + out_of_scope_bytes),
                  "producer_sha256": sha256_file(Path(__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    blob = build_bundles(dataset, chunk_size=args.chunk_size, checkpoint=checkpoint,
                         stop_after=args.stop_after_chunks)
    if blob is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(dataset.target_keys)) if checkpoint else 0,
                "target_count": len(dataset.target_keys)}
    payloads = split_bundles(blob)
    payloads["exclusions.jsonl"] = exclusions_bytes
    payloads["out_of_scope.jsonl"] = out_of_scope_bytes
    counts = {name: payloads[name].count(b"\n") for name in PAYLOAD_FILES}
    census_keys = [json.loads(line)["contest_key"] for name in ("targets.jsonl", "exclusions.jsonl",
                                                                  "out_of_scope.jsonl")
                   for line in payloads[name].decode("utf-8").splitlines()]
    if len(census_keys) != len(set(census_keys)) or set(census_keys) != {k for k, _s in dataset.census}:
        raise BuildRefused("CENSUS_INCOMPLETE", "targets, exclusions and out-of-scope do not partition the parent")
    if counts["history.jsonl"] != 2 * counts["targets.jsonl"] or counts["labels.jsonl"] != counts["targets.jsonl"]:
        raise BuildRefused("CENSUS_INCOMPLETE", "views or labels do not match the targets")
    parent_doc = {k: parent_binding[k] for k in ("query_db_identity", "sqlite_sha256", "contract_sha256",
                                                  "contest_identity", "program_season_identity")}
    content_document = {"schema": CONTENT_SCHEMA, "stage": "history-content", "population": POPULATION,
                        "contract_id": contract["contract_id"], "contract_sha256": contract_sha,
                        "parent": {**parent_doc, "schema_version": PARENT_DB_SCHEMA},
                        "payload_schema": PAYLOAD_SCHEMA,
                        "outputs": {name: sha256_bytes(payloads[name]) for name in PAYLOAD_FILES},
                        "row_counts": counts}
    content_identity = sha256_bytes(canonical_json_bytes(content_document))
    output_root, manifest_root = Path(args.output_root), Path(args.manifest_root)
    with tempfile.TemporaryDirectory(prefix="nhp-") as work:
        return _finish(args, contract, contract_sha, parent_binding, content_document, content_identity, payloads,
                       counts, output_root, manifest_root, Path(work) / DB_FILE, started)


def _finish(args: argparse.Namespace, contract: dict[str, Any], contract_sha: str, parent_binding: dict[str, Any],
            content_document: dict[str, Any], content_identity: str, payloads: dict[str, bytes],
            counts: dict[str, int], output_root: Path, manifest_root: Path, db_path: Path,
            started: float) -> dict[str, Any]:
    parent_doc = content_document["parent"]
    meta = {"schema_version": DB_SCHEMA, "contract_id": contract["contract_id"], "contract_sha256": contract_sha,
            "content_identity": content_identity, "payload_schema": PAYLOAD_SCHEMA,
            "payload_sha256": json.dumps(content_document["outputs"], sort_keys=True),
            "row_counts": json.dumps(counts, sort_keys=True),
            "parent": json.dumps(content_document["parent"], sort_keys=True),
            "row_labels": json.dumps(ROW_LABELS, sort_keys=True),
            "target_seasons": json.dumps(list(TARGET_SEASONS)), "prior_rule": PRIOR_RULE}
    table_counts = build_database(db_path, payloads, meta)
    database_document = {"schema": DATABASE_SCHEMA, "stage": "history-database", "population": POPULATION,
                         "contract_sha256": contract_sha, "content_identity": content_identity,
                         "db_schema_version": DB_SCHEMA, "outputs": {DB_FILE: sha256_file(db_path)},
                         "table_counts": table_counts}
    database_identity = sha256_bytes(canonical_json_bytes(database_document))
    provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                  "producer_sha256": sha256_file(Path(__file__)), "argv": list(args.argv),
                  "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                  "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                  "chunk_size": args.chunk_size, "resumed": bool(args.resume),
                  "jira_key": contract.get("jira_key"), "cycle_number": contract.get("cycle_number"),
                  "attempt_number": contract.get("attempt_number"), "parent_manifest": parent_binding["manifest"],
                  "database_identity": database_identity,
                  "database_manifest": f"sha256/{database_identity}/run_manifest.json"}
    content = materialize(output_root, manifest_root, content_document, dict(payloads), provenance)
    database = materialize(output_root, manifest_root, database_document, {DB_FILE: db_path},
                           {**provenance, "content_identity": content_identity})
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "content": content, "database": database, "row_counts": counts, "table_counts": table_counts,
            "payload_sha256": content_document["outputs"], "database_sha256": database_document["outputs"][DB_FILE],
            "contract_sha256": contract_sha, "parent": {k: v for k, v in parent_doc.items() if k != "schema_version"},
            "input_order": args.input_order, "chunk_size": args.chunk_size, "variant": args.variant,
            "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_history_prefix", allow_abbrev=False,
                                     description="Build the national 2016-2023 FBS retrospective history prefix.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--parent-database", required=True, type=Path)
    parser.add_argument("--parent-manifest", type=Path, default=None)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--input-order", default="natural")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--stop-after-chunks", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--variant", default="CANONICAL")
    parser.add_argument("--receipt", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw)
    args.argv = ["tools/build_national_history_prefix.py", *raw]
    try:
        result = build(args)
    except BuildRefused as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    text = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.receipt is not None:
        with Path(args.receipt).open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    sys.stdout.write(text)
    return INTERRUPTED_EXIT if result["state"] == "INTERRUPTED_AT_CHECKPOINT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
