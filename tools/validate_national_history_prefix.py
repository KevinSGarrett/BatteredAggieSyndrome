r"""Independent validator and oracle for the national 2016-2023 FBS history prefix (BAT-711, Cycle #39 TP39-A01).

``python -B tools/validate_national_history_prefix.py --contract configs/national_history_prefix_2016_2023_contract.json
--parent-database <bound parent national_population.sqlite> --manifest <manifests/.../sha256/<content id>/run_manifest.json>
--report <new report.json>``

Standard library only. It imports no producer, query or project module and never treats delivered rows as the expected
population. From the immutable parent it independently

1. rehashes the contract, the parent SQLite file and the parent manifest identity and checks every binding;
2. enumerates the 2016-2023 FBS_ESTIMAND_SUBSET targets and the history pool with its own SQL and predicate table;
3. reconstructs every target, both views, every contributing contest, integer total, rational rate, cold start and
   excluded input by brute-force linear scans (no shared index or helper), every exclusion and every out-of-scope key;
4. compares each delivered key and field, the canonical serialization, closed schemas, ordering, identities and the
   SQLite tables/meta with that reconstruction;
5. compares the parent SQLite rows with the parent contest-stage payload and traces a deterministic per-season sample
   (plus 2020 spring) of targets to the cited raw NCAA page bytes;
6. runs coordinated semantic tamper cases (outer hashes rehashed consistently) that must be rejected, and challenges
   its own reconstruction with wrong order/opponent/rate/season assumptions that must disagree with the delivery.

The report is create-only. Exit 0 only when every check passes; any disagreement is reported per key and field.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import gzip
import hashlib
import json
import math
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

TARGET_SEASONS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]
LABELS = {"observation_authority": "RETROSPECTIVE_OBSERVATION_ONLY",
          "pit_eligibility": "PIT_ELIGIBILITY_NOT_ESTABLISHED",
          "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME"}
PAYLOADS = ["targets.jsonl", "history.jsonl", "exclusions.jsonl", "labels.jsonl", "out_of_scope.jsonl"]
DB_NAME = "national_history.sqlite"
PARENT_NAME = "national_population.sqlite"
RAW_PARTS = ("raw", "SRC-015", "ncaa_team_season_discovery")
MAX_DETAILS = 40


def cjson(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(1 << 20)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


class Report:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, ok: bool, detail: Any = None, **extra: Any) -> bool:
        self.checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail, **extra})
        return ok

    @property
    def failed(self) -> list[str]:
        return [c["check"] for c in self.checks if c["result"] != "PASS"]


# ------------------------------------------------------------------------------------------------ parent reading

class Parent:
    """Independent read of the bound parent; never imports the producer."""

    COLUMNS = ["contest_key", "ncaa_contest_id", "season", "term", "contest_date", "site", "neutral_site_text",
               "contest_status", "competitive", "a_org_id", "a_team_season_id", "a_team_name", "a_division_label",
               "a_points", "b_org_id", "b_team_season_id", "b_team_name", "b_division_label", "b_points",
               "classification_pair", "source", "cfbd_game_ids", "reconciliation_state", "disposition", "a_key",
               "b_key", "contest_dates_observed"]

    def __init__(self, path: Path) -> None:
        uri = "file:" + str(Path(path).resolve()).replace("\\", "/") + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            self.meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
            self.all_keys = con.execute("SELECT contest_key, season FROM contest").fetchall()
            cols = ", ".join(self.COLUMNS)
            self.rows = []
            for values in con.execute(f"SELECT {cols} FROM contest WHERE season BETWEEN 2016 AND 2023"):
                self.rows.append(dict(zip(self.COLUMNS, values)))
            self.fbs = [k for (k,) in con.execute(
                "SELECT contest_key FROM subset_membership WHERE subset = 'FBS_ESTIMAND_SUBSET'")]
        finally:
            con.close()


def is_iso_day(text: Any) -> bool:
    if type(text) is not str or len(text) != 10 or text[4] != "-" or text[7] != "-":
        return False
    try:
        return datetime.date(int(text[0:4]), int(text[5:7]), int(text[8:10])).isoformat() == text
    except ValueError:
        return False


def pool_failures(row: dict[str, Any]) -> list[str]:
    """The contract predicate table, written independently of the producer."""
    out: list[str] = []
    checks: list[tuple[str, Callable[[], bool]]] = [
        ("DISPOSITION_NOT_VERIFIED_PRESENT", lambda: row["disposition"] == "VERIFIED_PRESENT"),
        ("RECONCILIATION_NOT_RECONCILED_2016_2023", lambda: row["reconciliation_state"] == "RECONCILED_2016_2023"),
        ("STATUS_NOT_COMPLETED", lambda: row["contest_status"] == "COMPLETED"),
        ("NOT_COMPETITIVE", lambda: type(row["competitive"]) is int and row["competitive"] == 1),
    ]
    for reason, test in checks:
        if not test():
            out.append(reason)
    if not is_iso_day(row["contest_date"]):
        out.append("DATE_INVALID")
    elif row["contest_dates_observed"] is not None:
        try:
            observed = json.loads(row["contest_dates_observed"])
        except (TypeError, ValueError):
            observed = None
        if not (isinstance(observed, list) and observed and all(d == row["contest_date"] for d in observed)):
            out.append("DATE_NOT_SINGLE")
    keys_ok = True
    for side in "ab":
        key, org = row[side + "_key"], row[side + "_org_id"]
        if not (type(key) is str and key.startswith("org:") and key[4:].isdigit() and key[4:] == str(org)):
            keys_ok = False
    if not keys_ok:
        out.append("ORG_KEY_NOT_STABLE")
    if row["a_key"] == row["b_key"]:
        out.append("ORG_KEYS_NOT_DISTINCT")
    pts = [row["a_points"], row["b_points"]]
    if None in pts:
        out.append("SCORE_MISSING")
    if any(p is not None and (type(p) is not int or p < 0) for p in pts):
        out.append("SCORE_NOT_NONNEGATIVE_INTEGER")
    return out


# ------------------------------------------------------------------------------------------------ expectation

class Expectation:
    """Brute-force reconstruction. ``assumptions`` lets the oracle challenge itself with deliberately wrong rules."""

    def __init__(self, parent: Parent, assumptions: dict[str, Any] | None = None) -> None:
        self.parent = parent
        self.a = {"date_op": "lt", "same_season": True, "opponent": "current", "swap_views": False,
                  "rates": "unreduced", "season_basis": "label", **(assumptions or {})}
        self.subset = set(parent.fbs)
        self.failures = {r["contest_key"]: pool_failures(r) for r in parent.rows}
        self.pool_rows = [r for r in parent.rows if not self.failures[r["contest_key"]]]
        self.bad_rows = [r for r in parent.rows if self.failures[r["contest_key"]]]
        self.targets = sorted((r for r in parent.rows
                               if r["contest_key"] in self.subset and not self.failures[r["contest_key"]]),
                              key=lambda r: (r["season"], r["contest_date"], r["contest_key"]))
        self._pool_by_season: dict[int, list[dict[str, Any]]] = {}
        self._bad_by_season: dict[int, list[dict[str, Any]]] = {}
        for r in self.pool_rows:
            self._pool_by_season.setdefault(self._season_of(r), []).append(r)
        for r in self.bad_rows:
            self._bad_by_season.setdefault(self._season_of(r), []).append(r)

    def _season_of(self, r: dict[str, Any]) -> int:
        if self.a["season_basis"] == "gregorian" and is_iso_day(r["contest_date"]):
            return int(r["contest_date"][:4])
        return r["season"]

    def _prior(self, season: int, team: str, date: str, target: str) -> list[dict[str, Any]]:
        candidates = []
        seasons = [season] if self.a["same_season"] else list(self._pool_by_season)
        for s in seasons:
            for r in self._pool_by_season.get(s, []):
                if team not in (r["a_key"], r["b_key"]):
                    continue
                if self.a["date_op"] == "lt" and r["contest_date"] < date:
                    candidates.append(r)
                elif self.a["date_op"] == "le" and r["contest_date"] <= date:
                    candidates.append(r)
                elif self.a["date_op"] == "all":
                    candidates.append(r)
        candidates.sort(key=lambda r: (r["contest_date"], r["contest_key"]))
        return candidates

    def block(self, season: int, team: str, date: str, target: str) -> dict[str, Any]:
        rows = self._prior(season, team, date, target)
        contributing = []
        w = l = t = pf_total = pa_total = 0
        for r in rows:
            mine = "a" if r["a_key"] == team else "b"
            theirs = "b" if mine == "a" else "a"
            pf, pa = r[mine + "_points"], r[theirs + "_points"]
            if pf > pa:
                res, w = "W", w + 1
            elif pf < pa:
                res, l = "L", l + 1
            else:
                res, t = "T", t + 1
            pf_total += pf
            pa_total += pa
            contributing.append({"contest_key": r["contest_key"], "contest_date": r["contest_date"],
                                 "side": mine.upper(), "opponent_key": r[theirs + "_key"],
                                 "opponent_division_label": r[theirs + "_division_label"], "points_for": pf,
                                 "points_against": pa, "result": res})
        n = len(rows)
        margin = pf_total - pa_total

        def ratio(num: int) -> dict[str, int] | None:
            if n == 0:
                return None
            if self.a["rates"] == "reduced":
                g = math.gcd(num, n) or 1
                return {"numerator": num // g, "denominator": n // g}
            return {"numerator": num, "denominator": n}
        excluded = []
        for r in self._pool_by_season.get(season, []):
            if team in (r["a_key"], r["b_key"]) and r["contest_date"] == date and r["contest_key"] != target:
                excluded.append({"contest_key": r["contest_key"], "contest_date": r["contest_date"],
                                 "opponent_key": r["b_key"] if r["a_key"] == team else r["a_key"],
                                 "reasons": ["SAME_DATE_NOT_STRICTLY_EARLIER"]})
        for r in self._bad_by_season.get(season, []):
            if team not in (r["a_key"], r["b_key"]):
                continue
            valid = is_iso_day(r["contest_date"])
            if valid and r["contest_date"] > date:
                continue
            reasons = list(self.failures[r["contest_key"]])
            if valid and r["contest_date"] == date:
                reasons.append("SAME_DATE_NOT_STRICTLY_EARLIER")
            excluded.append({"contest_key": r["contest_key"], "contest_date": r["contest_date"],
                             "opponent_key": r["b_key"] if r["a_key"] == team else r["a_key"], "reasons": reasons})
        excluded.sort(key=lambda e: (e["contest_date"] if is_iso_day(e["contest_date"]) else "", e["contest_key"]))
        return {"team_key": team, "season": season, "history_state": "HAS_PRIOR_CONTESTS" if n else "COLD_START",
                "games": n, "wins": w, "losses": l, "ties": t, "points_for_total": pf_total,
                "points_against_total": pa_total, "margin_total": margin, "rate_denominator": n,
                "win_rate": ratio(w), "points_for_mean": ratio(pf_total), "points_against_mean": ratio(pa_total),
                "margin_mean": ratio(margin), "contributing_contest_keys": [c["contest_key"] for c in contributing],
                "contributing": contributing, "excluded_inputs": excluded}

    def terminal_block(self, season: int, team: str) -> dict[str, Any]:
        return self.block(season, team, "9999-12-31", "")

    def target_record(self, r: dict[str, Any]) -> dict[str, Any]:
        try:
            cfbd = json.loads(r["cfbd_game_ids"]) if isinstance(r["cfbd_game_ids"], str) else (r["cfbd_game_ids"] or [])
        except ValueError:
            cfbd = [r["cfbd_game_ids"]]
        if not isinstance(cfbd, list):
            cfbd = [cfbd]
        out = {"record_type": "target", "views": ["A", "B"], "parent_site": r["site"],
               "parent_disposition": r["disposition"], "parent_reconciliation_state": r["reconciliation_state"],
               "cfbd_game_ids": cfbd, **LABELS}
        for name in ("contest_key", "ncaa_contest_id", "season", "term", "contest_date", "a_key", "b_key", "a_org_id",
                     "b_org_id", "a_team_name", "b_team_name", "a_team_season_id", "b_team_season_id",
                     "a_division_label", "b_division_label", "classification_pair", "neutral_site_text", "source"):
            out[name] = r[name]
        return out

    def history_records(self, r: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        for view, me, them in (("A", "a", "b"), ("B", "b", "a")):
            if self.a["swap_views"]:
                me, them = them, me
            team, opp = r[me + "_key"], r[them + "_key"]
            opp_block = (self.terminal_block(r["season"], opp) if self.a["opponent"] == "terminal"
                         else self.block(r["season"], opp, r["contest_date"], r["contest_key"]))
            out.append({"record_type": "history_view", "target_contest_key": r["contest_key"], "view": view,
                        "season": r["season"], "term": r["term"], "target_date": r["contest_date"],
                        "prior_rule": "SAME_SEASON_DATE_STRICTLY_BEFORE_TARGET_DATE", "team_key": team,
                        "team_org_id": r[me + "_org_id"], "team_name": r[me + "_team_name"],
                        "team_division_label": r[me + "_division_label"], "opponent_key": opp,
                        "opponent_org_id": r[them + "_org_id"], "opponent_name": r[them + "_team_name"],
                        "opponent_division_label": r[them + "_division_label"],
                        "team_history": self.block(r["season"], team, r["contest_date"], r["contest_key"]),
                        "opponent_history": opp_block, **LABELS})
        return out

    def label_record(self, r: dict[str, Any]) -> dict[str, Any]:
        a, b = r["a_points"], r["b_points"]

        def res(x: int, y: int) -> str:
            return "W" if x > y else ("L" if x < y else "T")
        return {"record_type": "target_label", "contest_key": r["contest_key"], "season": r["season"],
                "contest_date": r["contest_date"], "a_key": r["a_key"], "b_key": r["b_key"], "a_points": a,
                "b_points": b, "a_margin": a - b, "a_result": res(a, b), "b_result": res(b, a),
                "label_authority": "POSTGAME_OUTCOME_SEPARATED_FROM_HISTORY", **LABELS}

    def exclusion_records(self) -> list[dict[str, Any]]:
        target_keys = {r["contest_key"] for r in self.targets}
        out = []
        for r in self.parent.rows:
            if r["contest_key"] in target_keys:
                continue
            fails = self.failures[r["contest_key"]]
            member = r["contest_key"] in self.subset
            pts = [r["a_points"], r["b_points"]]
            state = ("MISSING" if None in pts else
                     ("NONNEGATIVE_INTEGERS" if all(type(p) is int and p >= 0 for p in pts) else "INVALID"))
            out.append({"record_type": "exclusion", "contest_key": r["contest_key"],
                        "ncaa_contest_id": r["ncaa_contest_id"], "season": r["season"], "term": r["term"],
                        "contest_date": r["contest_date"], "a_key": r["a_key"], "b_key": r["b_key"],
                        "a_team_name": r["a_team_name"], "b_team_name": r["b_team_name"],
                        "classification_pair": r["classification_pair"], "fbs_estimand_subset": member,
                        "target_exclusion_reasons": ([] if member else ["NOT_IN_FBS_ESTIMAND_SUBSET"]) + fails,
                        "history_pool_member": not fails, "history_pool_exclusion_reasons": list(fails),
                        "parent_disposition": r["disposition"], "parent_reconciliation_state": r["reconciliation_state"],
                        "parent_contest_status": r["contest_status"], "parent_competitive": r["competitive"],
                        "score_state": state, **LABELS})
        out.sort(key=lambda e: (e["season"], e["contest_date"] or "", e["contest_key"]))
        return out

    def out_of_scope_records(self) -> list[dict[str, Any]]:
        out = []
        for key, season in self.parent.all_keys:
            if season in TARGET_SEASONS:
                continue
            reason = "PROTECTED_EXPOSED_SEASON_2024_2025" if season in (2024, 2025) else "SEASON_OUTSIDE_2016_2023"
            out.append({"record_type": "out_of_scope", "contest_key": key, "season": season, "reason": reason, **LABELS})
        out.sort(key=lambda e: (e["season"], e["contest_key"]))
        return out


# ------------------------------------------------------------------------------------------------ comparison

def diff(expected: Any, actual: Any, path: str = "$", out: list[str] | None = None, limit: int = 8) -> list[str]:
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if type(expected) is not type(actual):
        out.append(f"{path}: type {type(expected).__name__} != {type(actual).__name__} ({expected!r} vs {actual!r})"[:300])
    elif isinstance(expected, dict):
        for k in sorted(set(expected) | set(actual)):
            if k not in actual:
                out.append(f"{path}.{k}: missing")
            elif k not in expected:
                out.append(f"{path}.{k}: unexpected field")
            else:
                diff(expected[k], actual[k], f"{path}.{k}", out, limit)
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            out.append(f"{path}: length {len(expected)} != {len(actual)}")
        for i, (e, a) in enumerate(zip(expected, actual)):
            diff(e, a, f"{path}[{i}]", out, limit)
    elif expected != actual:
        out.append(f"{path}: {expected!r} != {actual!r}"[:300])
    return out


def walk_floats(value: Any) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(walk_floats(v) for v in value.values())
    if isinstance(value, list):
        return any(walk_floats(v) for v in value)
    return False


def schema_problems(record: dict[str, Any], fields: dict[str, list[str]]) -> list[str]:
    problems = []
    kind = record.get("record_type")
    if kind not in fields or kind in ("history_block", "contributing", "excluded_input", "rate"):
        return [f"unknown record_type {kind!r}"]
    if set(record) != set(fields[kind]):
        problems.append(f"{kind} fields differ: {sorted(set(record) ^ set(fields[kind]))}")
    for name, value in LABELS.items():
        if record.get(name) != value:
            problems.append(f"{name} is {record.get(name)!r}")
    if kind == "history_view":
        for side in ("team_history", "opponent_history"):
            block = record.get(side) or {}
            if set(block) != set(fields["history_block"]):
                problems.append(f"{side} fields differ: {sorted(set(block) ^ set(fields['history_block']))}")
            for item in block.get("contributing") or []:
                if set(item) != set(fields["contributing"]):
                    problems.append(f"{side}.contributing fields differ: {sorted(set(item) ^ set(fields['contributing']))}")
            for item in block.get("excluded_inputs") or []:
                if set(item) != set(fields["excluded_input"]):
                    problems.append(f"{side}.excluded_inputs fields differ")
            for name in ("win_rate", "points_for_mean", "points_against_mean", "margin_mean"):
                rate = block.get(name)
                if rate is not None and (set(rate) != set(fields["rate"]) or rate.get("denominator") !=
                                         block.get("games") or not block.get("games")):
                    problems.append(f"{side}.{name} is not an unreduced games-denominator rational: {rate!r}")
                if rate is None and block.get("games"):
                    problems.append(f"{side}.{name} null with games {block.get('games')}")
    if walk_floats(record):
        problems.append("floating-point value present")
    return problems


def key_of(name: str, record: dict[str, Any]) -> Any:
    if name == "history.jsonl":
        return (record.get("target_contest_key"), record.get("view"))
    return record.get("contest_key")


def compare_payload(name: str, expected: list[dict[str, Any]], delivered: list[dict[str, Any]]) -> dict[str, Any]:
    exp = {key_of(name, r): r for r in expected}
    got: dict[Any, dict[str, Any]] = {}
    duplicates = []
    for r in delivered:
        k = key_of(name, r)
        if k in got:
            duplicates.append(k)
        got[k] = r
    missing = sorted(map(str, set(exp) - set(got)))
    extra = sorted(map(str, set(got) - set(exp)))
    mismatched = []
    for k in sorted(set(exp) & set(got), key=str):
        problems = diff(exp[k], got[k])
        if problems:
            mismatched.append({"key": str(k), "differences": problems})
    order_ok = [key_of(name, r) for r in delivered] == [key_of(name, r) for r in expected]
    return {"expected": len(exp), "delivered": len(delivered), "missing": missing[:MAX_DETAILS],
            "missing_count": len(missing), "extra": extra[:MAX_DETAILS], "extra_count": len(extra),
            "duplicates": [str(d) for d in duplicates[:MAX_DETAILS]], "duplicate_count": len(duplicates),
            "mismatched": mismatched[:MAX_DETAILS], "mismatched_count": len(mismatched), "order_matches": order_ok,
            "agree": not (missing or extra or duplicates or mismatched) and order_ok}


# ------------------------------------------------------------------------------------------------ delivered data

class Delivered:
    def __init__(self, manifest: Path) -> None:
        self.manifest_path = Path(manifest)
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.doc = self.manifest["identity_document"]
        self.identity_dir = self.manifest_path.parent.name
        manifest_root = self.manifest_path.parent.parent.parent
        self.data_root_population = manifest_root.parent.parent / "canonical" / manifest_root.name
        self.data_dir = self.data_root_population / "sha256" / self.identity_dir
        self.bytes = {n: (self.data_dir / n).read_bytes() for n in PAYLOADS}
        self.records = {n: [json.loads(line) for line in self.bytes[n].decode("utf-8").splitlines()] for n in PAYLOADS}
        pointer = (self.manifest.get("provenance") or {}).get("database_manifest")
        self.db_manifest_path = manifest_root / pointer if pointer else None
        self.db_manifest = json.loads(self.db_manifest_path.read_text(encoding="utf-8")) if pointer else None
        self.db_path = (self.data_root_population / "sha256" / self.db_manifest_path.parent.name / DB_NAME
                        if pointer else None)


def content_document_problems(doc: dict[str, Any], payload_bytes: dict[str, bytes], contract: dict[str, Any],
                              contract_sha: str) -> list[str]:
    problems = []
    binding = contract["parent_binding"]
    expected_parent = {"query_db_identity": binding["query_db_identity"], "sqlite_sha256": binding["sqlite_sha256"],
                       "contract_sha256": binding["contract_sha256"], "contest_identity": binding["contest_identity"],
                       "program_season_identity": binding["program_season_identity"],
                       "schema_version": binding["schema_version"]}
    if doc.get("parent") != expected_parent:
        problems.append("content identity document parent differs from the contract binding")
    if doc.get("contract_sha256") != contract_sha or doc.get("contract_id") != contract["contract_id"]:
        problems.append("content identity document contract differs")
    if (doc.get("stage"), doc.get("payload_schema")) != ("history-content", contract["payloads"]["schema_version"]):
        problems.append("content identity document stage/schema unknown")
    for n in PAYLOADS:
        if doc.get("outputs", {}).get(n) != digest(payload_bytes[n]):
            problems.append(f"{n} bytes do not hash to the content identity document")
        if doc.get("row_counts", {}).get(n) != payload_bytes[n].count(b"\n"):
            problems.append(f"{n} row count differs from the identity document")
    return problems


def serialization_problems(name: str, data: bytes) -> list[str]:
    problems = []
    if data.startswith(b"\xef\xbb\xbf"):
        problems.append("BOM present")
    if data and not data.endswith(b"\n"):
        problems.append("no final LF")
    if b"\r" in data or b"\n\n" in data:
        problems.append("CR or blank line present")
    for i, line in enumerate(data.split(b"\n")[:-1]):
        if cjson(json.loads(line.decode("utf-8"))) != line:
            problems.append(f"line {i + 1} is not canonical JSON")
            break
    return problems


# ------------------------------------------------------------------------------------------------ raw/upstream

def upstream_comparison(parent: Parent, data_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    binding = contract["parent_binding"]
    population = "national_di_population_2016_2025"
    manifest = data_root / "manifests" / population / "sha256" / binding["contest_identity"] / "run_manifest.json"
    payload = data_root / "canonical" / population / "sha256" / binding["contest_identity"] / "contests.jsonl.gz"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    ok_identity = digest(cjson(doc["identity_document"])) == binding["contest_identity"]
    ok_payload = doc["identity_document"]["outputs"].get("contests.jsonl.gz") == file_digest(payload)
    upstream = {}
    with gzip.open(payload, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if "_header" not in row:
                upstream[row["contest_key"]] = row
    fields = ["season", "term", "contest_date", "contest_status", "disposition", "reconciliation_state", "a_key",
              "b_key", "a_org_id", "b_org_id", "a_points", "b_points", "a_division_label", "b_division_label"]
    differences = []
    for r in parent.rows:
        u = upstream.get(r["contest_key"])
        if u is None:
            differences.append({"key": r["contest_key"], "problem": "absent upstream"})
            continue
        for f in fields:
            if u.get(f) != r[f]:
                differences.append({"key": r["contest_key"], "field": f, "sqlite": r[f], "upstream": u.get(f)})
        if bool(u.get("competitive")) != bool(r["competitive"]):
            differences.append({"key": r["contest_key"], "field": "competitive"})
    return {"manifest_identity_recomputes": ok_identity, "payload_hash_matches": ok_payload,
            "rows_compared": len(parent.rows), "fields": fields + ["competitive"],
            "differences": differences[:MAX_DETAILS], "difference_count": len(differences),
            "agree": ok_identity and ok_payload and not differences}


DATE_RE = re.compile(r"<td>\s*(\d{2})/(\d{2})/(\d{4})\s*</td>")
RESULT_RE = re.compile(r"([WLT])\s+(\d+)\s*-\s*(\d+)")


def raw_sample(expectation: Expectation, data_root: Path, contract: dict[str, Any], per_stratum: int) -> dict[str, Any]:
    """Deterministic per-stratum sample: targets of each season, the 2020 targets dated in 2021, and the 2020 spring
    term (no 2020 spring contest is an FBS target, so that stratum samples the spring history-pool contests)."""
    strata: dict[str, list[dict[str, Any]]] = {}
    for r in expectation.targets:
        strata.setdefault(str(r["season"]), []).append(r)
        if r["season"] == 2020 and r["contest_date"] >= "2021-01-01":
            strata.setdefault("2020_TARGETS_DATED_2021", []).append(r)
    for r in expectation.pool_rows:
        if r["season"] == 2020 and r["term"] == "SPRING":
            strata.setdefault("2020_SPRING_POOL", []).append(r)
    chosen = {name: sorted(rows, key=lambda r: digest(r["contest_key"].encode()))[:per_stratum]
              for name, rows in sorted(strata.items())}
    wanted = {r["ncaa_contest_id"] for rows in chosen.values() for r in rows}
    binding = contract["parent_binding"]
    pages = data_root / "canonical" / "national_di_population_2016_2025" / "sha256" / \
        binding["program_season_identity"] / "page_observations.jsonl.gz"
    observations: dict[str, list[dict[str, Any]]] = {}
    with gzip.open(pages, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("ncaa_contest_id") in wanted:
                observations.setdefault(row["ncaa_contest_id"], []).append(row)
    raw_dir = data_root.joinpath(*RAW_PARTS)
    results = []
    for stratum, rows in chosen.items():
        for r in rows:
            entry = {"stratum": stratum, "contest_key": r["contest_key"], "pages": []}
            for obs in observations.get(r["ncaa_contest_id"], []):
                side = ("a" if obs.get("page_team_season_id") == r["a_team_season_id"] else
                        "b" if obs.get("page_team_season_id") == r["b_team_season_id"] else None)
                page = {"page_raw_sha256": obs.get("page_raw_sha256"), "side": side}
                path = raw_dir / f"{obs.get('page_raw_sha256')}.html"
                if side is None or not path.is_file():
                    page["agree"] = False
                    page["problem"] = "page side unresolved or raw file absent"
                    entry["pages"].append(page)
                    continue
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="replace")
                page["raw_hash_matches"] = digest(raw) == obs["page_raw_sha256"]
                anchor = text.find(f"/contests/{r['ncaa_contest_id']}/")
                row_start = text.rfind("<tr", 0, anchor) if anchor >= 0 else -1
                date_match = DATE_RE.search(text, row_start) if row_start >= 0 else None
                result_match = RESULT_RE.search(text, anchor) if anchor >= 0 else None
                mine, theirs = r[side + "_points"], r[("b" if side == "a" else "a") + "_points"]
                if date_match:
                    page["raw_date"] = f"{date_match.group(3)}-{date_match.group(1)}-{date_match.group(2)}"
                if result_match:
                    page["raw_result"] = result_match.group(0)
                page["agree"] = bool(page["raw_hash_matches"] and date_match and result_match
                                     and page["raw_date"] == r["contest_date"]
                                     and int(result_match.group(2)) == mine and int(result_match.group(3)) == theirs)
                entry["pages"].append(page)
            entry["agree"] = bool(entry["pages"]) and all(p["agree"] for p in entry["pages"])
            results.append(entry)
    return {"per_stratum": per_stratum, "strata": {k: len(v) for k, v in chosen.items()},
            "sampled_contests": len(results), "pages_checked": sum(len(e["pages"]) for e in results),
            "disagreements": [e for e in results if not e["agree"]][:MAX_DETAILS],
            "agree": bool(results) and all(e["agree"] for e in results), "samples": results,
            "limits": "deterministic first-N by sha256(contest_key) per season target stratum, the 2020 targets "
                      "dated in 2021 and the 2020 spring history-pool contests (no FBS target falls in 2020 spring); "
                      "only the "
                      "participants' own NCAA schedule pages (SRC-015) are re-read; box scores, CFBD second-source "
                      "rows and non-sampled contests are not re-parsed from raw bytes by this oracle"}


# ------------------------------------------------------------------------------------------------ database

def database_comparison(delivered: Delivered, contract_sha: str, content_identity: str) -> dict[str, Any]:
    problems = []
    dm = delivered.db_manifest
    if dm is None:
        return {"agree": False, "problems": ["content manifest names no database manifest"]}
    doc = dm["identity_document"]
    identity = digest(cjson(doc))
    if identity != dm.get("identity") or identity != delivered.db_manifest_path.parent.name:
        problems.append("database identity document does not hash to its directory")
    if doc.get("content_identity") != content_identity or doc.get("contract_sha256") != contract_sha:
        problems.append("database identity document names a different content identity or contract")
    if doc.get("outputs", {}).get(DB_NAME) != file_digest(delivered.db_path):
        problems.append("database bytes do not hash to the database identity document")
    uri = "file:" + str(delivered.db_path.resolve()).replace("\\", "/") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("meta", "targets", "history", "exclusions", "target_labels")}
        tables = {"targets": "targets.jsonl", "history": "history.jsonl", "exclusions": "exclusions.jsonl",
                  "target_labels": "labels.jsonl"}
        for table, payload in tables.items():
            stored = [rec for (rec,) in con.execute(f"SELECT record FROM {table} ORDER BY ord")]
            lines = delivered.bytes[payload].decode("utf-8").splitlines()
            if stored != lines:
                problems.append(f"table {table} records differ from {payload}")
        history_columns = con.execute("SELECT target_contest_key, view, team_key, opponent_key, record FROM history").fetchall()
        for key, view, team, opp, rec in history_columns:
            parsed = json.loads(rec)
            if (parsed["target_contest_key"], parsed["view"], parsed["team_key"], parsed["opponent_key"]) != (key, view, team, opp):
                problems.append(f"history index columns disagree with the record for {key}/{view}")
                break
    finally:
        con.close()
    if counts != doc.get("table_counts"):
        problems.append(f"table counts {counts} differ from the identity document")
    if meta.get("content_identity") != content_identity or meta.get("contract_sha256") != contract_sha:
        problems.append("database meta names a different content identity or contract")
    if json.loads(meta.get("row_labels", "null")) != LABELS:
        problems.append("database meta row labels differ")
    if json.loads(meta.get("payload_sha256", "null")) != {n: digest(delivered.bytes[n]) for n in PAYLOADS}:
        problems.append("database meta payload hashes differ")
    return {"database_identity": delivered.db_manifest_path.parent.name, "table_counts": counts,
            "problems": problems, "agree": not problems}


# ------------------------------------------------------------------------------------------------ tamper / challenge

def semantic_verdict(expected: dict[str, list[dict[str, Any]]], records: dict[str, list[dict[str, Any]]],
                     fields: dict[str, list[str]]) -> list[str]:
    """Return the payloads that disagree with the independent reconstruction (schema or values)."""
    rejected = []
    for name in PAYLOADS:
        bad_schema = any(schema_problems(r, fields) for r in records[name])
        if bad_schema or not compare_payload(name, expected[name], records[name])["agree"]:
            rejected.append(name)
    return rejected


def tamper_cases(expectation: Expectation, delivered: Delivered, expected: dict[str, list[dict[str, Any]]],
                 fields: dict[str, list[str]], contract: dict[str, Any], contract_sha: str) -> list[dict[str, Any]]:
    base = delivered.records
    hist = base["history.jsonl"]
    last_date: dict[tuple[int, str], str] = {}
    for r in hist:
        key = (r["season"], r["team_key"])
        last_date[key] = max(last_date.get(key, ""), r["target_date"])
    with_prior = next(i for i, r in enumerate(hist) if r["team_history"]["games"] >= 2
                      and last_date[(r["season"], r["team_key"])] > r["target_date"])
    cold = next((i for i, r in enumerate(hist) if r["team_history"]["games"] == 0), None)
    excl_missing = next((i for i, r in enumerate(base["exclusions.jsonl"]) if r["score_state"] == "MISSING"), None)
    missing_input = next(((i, side) for i, r in enumerate(hist) for side in ("team_history", "opponent_history")
                          if any("SCORE_MISSING" in e["reasons"] for e in r[side]["excluded_inputs"])), None)
    target_rows = {r["contest_key"]: r for r in expectation.targets}
    later_season_key = next((k for k, s in expectation.parent.all_keys if s in (2024, 2025)), None)

    def mutate(case: str) -> dict[str, list[dict[str, Any]]]:
        # Shallow list copies; only the records a case changes are deep-copied, so the delivery is never mutated.
        rec = {n: list(base[n]) for n in PAYLOADS}
        h = rec["history.jsonl"]
        h[with_prior] = copy.deepcopy(h[with_prior])
        row = h[with_prior]
        blk = row["team_history"]
        if case == "SWAP_CURRENT_OPPONENT":
            other = next(r for r in h if r["opponent_key"] != row["opponent_key"] and r["season"] == row["season"])
            row["opponent_key"], row["opponent_history"] = other["opponent_key"], copy.deepcopy(other["opponent_history"])
        elif case == "TERMINAL_OPPONENT":
            r = target_rows[row["target_contest_key"]]
            row["opponent_history"] = expectation.terminal_block(r["season"], row["opponent_key"])
        elif case == "TARGET_RESULT_IN_HISTORY":
            lab = next(x for x in rec["labels.jsonl"] if x["contest_key"] == row["target_contest_key"])
            mine = "a" if lab["a_key"] == row["team_key"] else "b"
            pf, pa = lab[mine + "_points"], lab[("b" if mine == "a" else "a") + "_points"]
            blk["contributing"].append({"contest_key": row["target_contest_key"], "contest_date": row["target_date"],
                                        "side": mine.upper(), "opponent_key": row["opponent_key"],
                                        "opponent_division_label": row["opponent_division_label"], "points_for": pf,
                                        "points_against": pa, "result": "W" if pf > pa else "L"})
            blk["contributing_contest_keys"].append(row["target_contest_key"])
            blk["games"] += 1
            blk["rate_denominator"] += 1
        elif case == "FUTURE_CONTEST_IN_HISTORY":
            later = next(x for x in h if x["team_key"] == row["team_key"] and x["season"] == row["season"]
                         and x["target_date"] > row["target_date"])
            blk["contributing_contest_keys"].append(later["target_contest_key"])
            blk["contributing"].append(dict(blk["contributing"][-1], contest_key=later["target_contest_key"],
                                            contest_date=later["target_date"]))
        elif case == "DUPLICATE_ORIENTATION":
            h.insert(with_prior + 1, copy.deepcopy(row))
        elif case == "DROP_EXCLUDED_KEY":
            rec["exclusions.jsonl"].pop(0)
        elif case == "MISSING_SCORE_AS_ZERO_IN_HISTORY" and missing_input is not None:
            index, side = missing_input
            h[index] = copy.deepcopy(h[index])
            block = h[index][side]
            gone = next(e for e in block["excluded_inputs"] if "SCORE_MISSING" in e["reasons"])
            block["excluded_inputs"].remove(gone)
            block["contributing"].append({"contest_key": gone["contest_key"], "contest_date": gone["contest_date"],
                                          "side": "A", "opponent_key": gone["opponent_key"],
                                          "opponent_division_label": "FBS", "points_for": 0, "points_against": 0,
                                          "result": "T"})
            block["contributing_contest_keys"].append(gone["contest_key"])
            block["games"] += 1
            block["ties"] += 1
            block["rate_denominator"] += 1
        elif case == "PROJECT_DIVISION_BACKWARD":
            blk["contributing"][0]["opponent_division_label"] = (
                "FBS" if blk["contributing"][0]["opponent_division_label"] != "FBS" else "FCS")
        elif case == "INJECT_PROTECTED_SEASON":
            rec["exclusions.jsonl"].append(dict(rec["exclusions.jsonl"][0], contest_key=later_season_key, season=2024))
        elif case == "INJECT_2026_TARGET":
            rec["targets.jsonl"].append(dict(rec["targets.jsonl"][0], contest_key="ncaa:2026000001", season=2026,
                                             contest_date="2026-08-29"))
        elif case == "MISSING_SCORE_AS_ZERO" and excl_missing is not None:
            rec["exclusions.jsonl"][excl_missing] = dict(rec["exclusions.jsonl"][excl_missing],
                                                         score_state="NONNEGATIVE_INTEGERS")
        elif case == "FABRICATED_KNOWN_AT":
            row["known_at"] = row["target_date"] + "T00:00:00Z"
        elif case == "RANK_VENUE_ELO_FEATURES":
            blk["elo"] = 1500
            blk["home_win_rate"] = blk["win_rate"]
        elif case == "ALTERED_RATIONAL_DENOMINATOR":
            blk["win_rate"] = {"numerator": blk["wins"], "denominator": blk["games"] + 1}
        elif case == "FABRICATED_ZERO_COLD_START":
            if cold is not None:
                h[cold] = copy.deepcopy(h[cold])
            target = h[cold] if cold is not None else row
            target["team_history"]["win_rate"] = {"numerator": 0, "denominator": 1}
        elif case == "LABEL_IN_HISTORY":
            row["team_points"] = 1
        elif case == "FORGED_PIT_LABEL":
            row["pit_eligibility"] = "PIT_ELIGIBLE"
        return rec

    cases = ["SWAP_CURRENT_OPPONENT", "TERMINAL_OPPONENT", "TARGET_RESULT_IN_HISTORY", "FUTURE_CONTEST_IN_HISTORY",
             "DUPLICATE_ORIENTATION", "DROP_EXCLUDED_KEY", "PROJECT_DIVISION_BACKWARD", "INJECT_PROTECTED_SEASON",
             "INJECT_2026_TARGET", "MISSING_SCORE_AS_ZERO", "MISSING_SCORE_AS_ZERO_IN_HISTORY",
             "FABRICATED_KNOWN_AT", "RANK_VENUE_ELO_FEATURES",
             "ALTERED_RATIONAL_DENOMINATOR", "FABRICATED_ZERO_COLD_START", "LABEL_IN_HISTORY", "FORGED_PIT_LABEL"]
    results = []
    for case in cases:
        rec = mutate(case)
        data = {n: b"".join(cjson(r) + b"\n" for r in rec[n]) for n in PAYLOADS}
        doc = copy.deepcopy(delivered.doc)  # coordinated rehash: the outer documents agree with the tampered bytes
        doc["outputs"] = {n: digest(data[n]) for n in PAYLOADS}
        doc["row_counts"] = {n: data[n].count(b"\n") for n in PAYLOADS}
        outer = content_document_problems(doc, data, contract, contract_sha)
        rejected = semantic_verdict(expected, rec, fields)
        results.append({"case": case, "outer_hashes_consistent": not outer, "rejected_payloads": rejected,
                        "rejected": bool(rejected)})
    # A changed parent with a consistently rehashed child: the binding check, not a stale hash, must refuse it.
    doc = copy.deepcopy(delivered.doc)
    doc["parent"]["sqlite_sha256"] = "0" * 64
    outer = content_document_problems(doc, delivered.bytes, contract, contract_sha)
    results.append({"case": "CHANGED_PARENT_REHASHED_CHILD", "outer_hashes_consistent": True,
                    "rejected_payloads": [], "binding_problems": outer, "rejected": bool(outer)})
    return results


def challenges(parent: Parent, delivered: Delivered, sample_keys: list[str]) -> list[dict[str, Any]]:
    """Wrong assumptions must disagree with the delivery; the stated rule must agree (on the same sample)."""
    variants = {"CORRECT_RULE": {}, "DATE_LE_INCLUDES_SAME_DATE": {"date_op": "le"},
                "ALL_SEASON_DATES": {"date_op": "all"}, "IGNORE_SEASON_LABEL": {"same_season": False},
                "TERMINAL_OPPONENT": {"opponent": "terminal"}, "SWAPPED_VIEWS": {"swap_views": True},
                "REDUCED_RATES": {"rates": "reduced"}, "GREGORIAN_2020": {"season_basis": "gregorian"}}
    by_key = {(r["target_contest_key"], r["view"]): r for r in delivered.records["history.jsonl"]}
    out = []
    for name, assumptions in variants.items():
        e = Expectation(parent, assumptions)
        rows = {r["contest_key"]: r for r in e.targets}
        compared = disagreeing = 0
        for key in sample_keys:
            if key not in rows:
                disagreeing += 1
                continue
            for rec in e.history_records(rows[key]):
                compared += 1
                if diff(rec, by_key.get((rec["target_contest_key"], rec["view"]))):
                    disagreeing += 1
        expectation_ok = (disagreeing == 0) if name == "CORRECT_RULE" else (disagreeing > 0)
        out.append({"assumption": name, "compared": compared, "disagreeing": disagreeing,
                    "expected_outcome": "AGREE" if name == "CORRECT_RULE" else "DISAGREE",
                    "as_expected": expectation_ok})
    return out


# ------------------------------------------------------------------------------------------------ main

def validate(args: argparse.Namespace) -> dict[str, Any]:
    rep = Report()
    contract_bytes = Path(args.contract).read_bytes()
    contract_sha = digest(contract_bytes)
    contract = json.loads(contract_bytes.decode("utf-8"))
    fields = contract["payloads"]["record_fields"]
    rep.check("contract_authority_labels", contract["authority"].get("observation_authority") == LABELS[
        "observation_authority"] and contract["authority"].get("pit_eligibility") == LABELS["pit_eligibility"] and
        contract["authority"].get("temporal_basis") == LABELS["temporal_basis"] and
        contract["payloads"].get("row_labels") == LABELS)
    rep.check("contract_target_seasons", contract["scope"]["target_seasons"] == TARGET_SEASONS and
              not set(contract["scope"]["target_seasons"]) & {2024, 2025, 2026})
    binding = contract["parent_binding"]
    parent_path = Path(args.parent_database)
    parent_sha = file_digest(parent_path)
    rep.check("parent_sqlite_sha256", parent_sha == binding["sqlite_sha256"], parent_sha)
    rep.check("parent_location", parent_path.name == PARENT_NAME and
              parent_path.resolve().parent.name == binding["query_db_identity"])
    pm_path = Path(args.parent_manifest) if args.parent_manifest else (
        parent_path.resolve().parent.parent.parent.parent.parent / "manifests" /
        parent_path.resolve().parent.parent.parent.name / "sha256" / binding["query_db_identity"] / "run_manifest.json")
    pm = json.loads(pm_path.read_text(encoding="utf-8"))
    pdoc = pm["identity_document"]
    rep.check("parent_manifest_identity", digest(cjson(pdoc)) == binding["query_db_identity"] == pm.get("identity")
              and pdoc.get("outputs", {}).get(PARENT_NAME) == parent_sha
              and pdoc.get("contract_sha256") == binding["contract_sha256"]
              and pdoc.get("upstream", {}).get("contest") == binding["contest_identity"]
              and pdoc.get("upstream", {}).get("program-season") == binding["program_season_identity"])
    parent = Parent(parent_path)
    rep.check("parent_meta", parent.meta.get("schema_version") == binding["schema_version"]
              and parent.meta.get("contract_sha256") == binding["contract_sha256"]
              and parent.meta.get("contest_identity") == binding["contest_identity"])
    keys = [k for k, _ in parent.all_keys]
    rep.check("parent_keys_unique", len(keys) == len(set(keys)), {"rows": len(keys)})
    expectation = Expectation(parent)
    in_scope = {r["contest_key"]: r for r in parent.rows}
    fbs_in_scope = [k for k in parent.fbs if k in in_scope]
    both_fbs = {k for k, r in in_scope.items() if r["a_division_label"] == "FBS" and r["b_division_label"] == "FBS"}
    rep.check("subset_field_consistency_both_directions", set(fbs_in_scope) == both_fbs,
              {"subset_2016_2023": len(fbs_in_scope), "both_fbs_labels": len(both_fbs)})

    delivered = Delivered(Path(args.manifest))
    identity = digest(cjson(delivered.doc))
    rep.check("content_identity_recomputes", identity == delivered.identity_dir == delivered.manifest.get("identity"),
              identity)
    rep.check("content_identity_document", not content_document_problems(delivered.doc, delivered.bytes, contract,
                                                                          contract_sha),
              content_document_problems(delivered.doc, delivered.bytes, contract, contract_sha))
    rep.check("data_dir_files", sorted(p.name for p in delivered.data_dir.iterdir()) == sorted(PAYLOADS))
    for n in PAYLOADS:
        rep.check(f"serialization:{n}", not serialization_problems(n, delivered.bytes[n]),
                  serialization_problems(n, delivered.bytes[n]))
        bad = [(key_of(n, r), schema_problems(r, fields)) for r in delivered.records[n] if schema_problems(r, fields)]
        rep.check(f"closed_schema:{n}", not bad, [str(b) for b in bad[:10]])

    expected = {"targets.jsonl": [expectation.target_record(r) for r in expectation.targets],
                "history.jsonl": [h for r in expectation.targets for h in expectation.history_records(r)],
                "labels.jsonl": [expectation.label_record(r) for r in expectation.targets],
                "exclusions.jsonl": expectation.exclusion_records(),
                "out_of_scope.jsonl": expectation.out_of_scope_records()}
    comparisons = {n: compare_payload(n, expected[n], delivered.records[n]) for n in PAYLOADS}
    for n, result in comparisons.items():
        rep.check(f"reconstruction:{n}", result["agree"], {k: v for k, v in result.items() if k != "agree"})
    census = [r["contest_key"] for n in ("targets.jsonl", "exclusions.jsonl", "out_of_scope.jsonl")
              for r in delivered.records[n]]
    rep.check("census_partition", len(census) == len(set(census)) and set(census) == set(keys),
              {"delivered_keys": len(census), "parent_keys": len(keys)})
    history_keys = {(r["target_contest_key"], r["view"]) for r in delivered.records["history.jsonl"]}
    rep.check("two_views_per_target", history_keys == {(r["contest_key"], v) for r in delivered.records["targets.jsonl"]
                                                       for v in ("A", "B")})
    label_free = all(not ({"a_points", "b_points", "team_points", "opponent_points", "a_result", "result",
                           "a_margin"} & set(r)) for n in ("targets.jsonl", "history.jsonl")
                     for r in delivered.records[n])
    rep.check("target_labels_absent_from_history_projection", label_free)
    target_dates = {r["contest_key"]: (r["season"], r["contest_date"]) for r in delivered.records["targets.jsonl"]}
    leaks = [(r["target_contest_key"], r["view"]) for r in delivered.records["history.jsonl"]
             for blk in (r["team_history"], r["opponent_history"]) for c in blk["contributing"]
             if not c["contest_date"] < r["target_date"] or c["contest_key"] == r["target_contest_key"]]
    rep.check("no_same_date_or_future_contributor", not leaks, leaks[:10])
    rep.check("no_protected_or_prospective_rows", all(r["season"] in TARGET_SEASONS for n in (
        "targets.jsonl", "history.jsonl", "exclusions.jsonl", "labels.jsonl") for r in delivered.records[n]))
    db = database_comparison(delivered, contract_sha, identity)
    rep.check("database", db["agree"], db)

    data_root = Path(args.data_root) if args.data_root else parent_path.resolve().parents[4]
    upstream = None
    raw = None
    if args.raw_sample_per_stratum > 0:
        upstream = upstream_comparison(parent, data_root, contract)
        rep.check("parent_sqlite_equals_contest_stage_payload", upstream["agree"],
                  {k: v for k, v in upstream.items() if k != "agree"})
        raw = raw_sample(expectation, data_root, contract, args.raw_sample_per_stratum)
        rep.check("raw_page_sample", raw["agree"], {k: v for k, v in raw.items() if k not in ("agree", "samples")})
    tampers = tamper_cases(expectation, delivered, expected, fields, contract, contract_sha)
    rep.check("coordinated_tamper_rejected", all(t["rejected"] for t in tampers),
              [t["case"] for t in tampers if not t["rejected"]])
    sample = sorted(target_dates, key=lambda k: digest(k.encode()))[:args.challenge_sample]
    cross_year = [r["contest_key"] for r in expectation.targets if r["season"] == 2020
                  and (r["term"] == "SPRING" or r["contest_date"] >= "2021-01-01")]
    sample = sorted(set(sample) | set(cross_year))
    challenge = challenges(parent, delivered, sample)
    rep.check("oracle_self_challenge", all(c["as_expected"] for c in challenge),
              [c for c in challenge if not c["as_expected"]])

    per_season = {}
    for r in delivered.records["targets.jsonl"]:
        per_season[r["season"]] = per_season.get(r["season"], 0) + 1
    histories = delivered.records["history.jsonl"]
    return {"validator": "validate_national_history_prefix/1.0.0", "result": "FAIL" if rep.failed else "PASS",
            "failed_checks": rep.failed, "contract_sha256": contract_sha, "contract_id": contract["contract_id"],
            "parent": {"sqlite_sha256": parent_sha, "query_db_identity": binding["query_db_identity"]},
            "content_identity": identity, "database_identity": db.get("database_identity"),
            "counts": {"parent_contests": len(keys), "parent_2016_2023": len(parent.rows),
                       "fbs_subset_2016_2023": len(fbs_in_scope), "history_pool": len(expectation.pool_rows),
                       "targets": len(expectation.targets), "views": len(histories),
                       "exclusions": len(expected["exclusions.jsonl"]),
                       "out_of_scope": len(expected["out_of_scope.jsonl"]), "targets_by_season": per_season,
                       "cold_start_blocks": sum(1 for r in histories for b in ("team_history", "opponent_history")
                                                if r[b]["games"] == 0),
                       "contributing_entries": sum(len(r[b]["contributing"]) for r in histories
                                                   for b in ("team_history", "opponent_history")),
                       "excluded_input_entries": sum(len(r[b]["excluded_inputs"]) for r in histories
                                                     for b in ("team_history", "opponent_history"))},
            "checks": rep.checks, "upstream_comparison": upstream, "raw_sample": raw, "tamper_cases": tampers,
            "oracle_challenges": challenge,
            "independence": "standard library only; no producer/query/project import; expectation rebuilt from the "
                            "parent by linear scans; delivered rows are compared, never used as the expected set",
            "non_claims": ["calendar order only; no PIT or known-at authority", "no predictive skill",
                           "worker oracle, not independent manager acceptance"]}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="validate_national_history_prefix", allow_abbrev=False)
    p.add_argument("--contract", required=True)
    p.add_argument("--parent-database", required=True)
    p.add_argument("--parent-manifest", default=None)
    p.add_argument("--manifest", required=True, help="content run manifest of the delivered history prefix")
    p.add_argument("--report", required=True)
    p.add_argument("--data-root", default=None)
    p.add_argument("--raw-sample-per-stratum", type=int, default=5)
    p.add_argument("--challenge-sample", type=int, default=400)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate(args)
    with open(args.report, "x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({"result": report["result"], "failed_checks": report["failed_checks"],
                      "content_identity": report["content_identity"], "database_identity": report["database_identity"],
                      "counts": report["counts"]}, indent=1))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
