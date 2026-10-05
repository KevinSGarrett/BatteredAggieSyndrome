r"""Independent validator for the BAT-715 archived-publication expansion (Cycle #43 TP43-A01).

``python -B tools/validate_national_archived_publication_expansion.py --contract
configs/national_archived_publication_2019_expansion_contract.json --source-database <bound source-time sqlite>
--source-bindings <Cycle 43 INPUT_BINDINGS.json> --tranche <ARCHIVE_TRANCHE.json> --cohort <ARCHIVE_COHORT.json>
--manifest <manifests/national_archived_publication_2019_expansion/sha256/<content id>/run_manifest.json>
--report <new path> [--retained-root <canonical/national_archived_publication_2019>] [--retained-contract <V1.2>]``

Standard library only; it imports no producer, query or project code. It loads the accepted Cycle 41 independent
oracle (``tools/validate_national_archived_publication.py``) by path only after its bytes hash to the accepted value
below, and reuses that oracle's own byte scanner, page/receipt/participant reconstruction, record comparison, consumer
decision rules, tamper machinery and self-challenges unchanged. On top of it this tool:

* rebuilds the 97-key union from the issued tranche and cohort bytes itself (tranche order, then the cohort's new keys
  in cohort order) and requires every declared key spec to equal its tranche/cohort rows;
* re-verifies the retained V1.2 acquisition, its policy recomputed from the committed V1.2 contract (hash-bound), and
  checks its copy in the expansion root byte-identical with the read-only V1.2 root;
* re-reads the expansion acquisition and its append-only journal: the declared probe timestamps, per-key and total
  limits, purposes, URLs, start spacing, retained bodies and the zero-request control;
* reconstructs every union disposition, request (with its acquisition identity), capture and assertion from both
  receipt documents in order, applying the duplicate-version rule itself; and
* adds union tamper cases (selection sources, outcome history, failed outcome relabelled captured, request moved
  between acquisitions, cohort key classified, hidden duplicate, retained requests dropped).

The report is a new file written once. Exit 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import re
import sqlite3
import zlib
from pathlib import Path
from typing import Any
from urllib.parse import unquote

ACCEPTED_ORACLE = Path(__file__).resolve().with_name("validate_national_archived_publication.py")
ACCEPTED_ORACLE_SHA256 = "091a6a90c1bcf417c4ec0ca57477ed610917dee1872e5adb2711f422865f5ec3"
EXPANSION_CONTRACT_ID = "BAT-715-NATIONAL-ARCHIVED-PUBLICATION-2019-EXPANSION-V1.0"
COHORT_ROLE = "COHORT_MISSING_PRIOR"
COHORT_STRATUM = "COHORT_2019_09_05_TO_08_TARGET_MISSING_PRIOR"
V12_CONTRACT = Path(__file__).resolve().parents[1] / "configs" / "national_archived_publication_2019_contract_v1_2.json"
RETAINED_ORIGIN = "RETAINED_V1_2_ACQUISITION_ZERO_NEW_REQUESTS"
EXPANSION_ORIGIN = "EXPANSION_ACQUISITION_COHORT_70"


def _load_accepted_oracle() -> Any:
    data = ACCEPTED_ORACLE.read_bytes()
    if hashlib.sha256(data).hexdigest() != ACCEPTED_ORACLE_SHA256:
        raise SystemExit(f"the accepted archive oracle bytes differ from {ACCEPTED_ORACLE_SHA256}")
    spec = importlib.util.spec_from_file_location("bas_c41_accepted_archive_oracle", ACCEPTED_ORACLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_accepted_oracle()
h_bytes, h_file, cjson, Report = base.h_bytes, base.h_file, base.cjson, base.Report
read_delivered, compare, clean, lines_of = base.read_delivered, base.compare, base.clean, base.lines_of
QUAL, SUPPORTABLE, FIELD_LIST, PAYLOAD_NAMES = base.QUAL, base.SUPPORTABLE, base.FIELD_LIST, base.PAYLOAD_NAMES


class Expected(base.Expected):
    """The accepted oracle's reconstruction, with the union's version collection and records."""

    def versions(self, key: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
        return self.union_versions(key, spec)[0]

    def union_versions(self, key: str, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """The control (if any), then each acquisition's HTTP 200 replays in acquisition and request order; a later
        version whose wayback timestamp and payload hash equal an earlier one is listed as a duplicate, not kept."""
        raw: list[dict[str, Any]] = []
        if spec["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL":
            raw += base.Expected(self.contract, dict(self.ctx, acquisition={"requests": []})).versions(key, spec)
        for acq_id, doc in self.ctx["acquisitions"]:
            for i, req in enumerate(doc["requests"]):
                if req["contest_key"] != key or req["kind"] != "REPLAY" or req["http_status"] != 200:
                    continue
                where = f"acquisition/sha256/{acq_id}/acquisition.json"
                raw.append({"origin": "WORKER_ARCHIVE_REPLAY", "seq": req["seq"], "url": req["url"],
                            "status": req["http_status"], "headers": req["headers"],
                            "payload": self.raw(req["body_sha256"]), "receipt_document": where,
                            "receipt_document_sha256": acq_id, "receipt_pointer": f"/requests/{i}",
                            "retrieval": {"state": "PRESENT", "role": "EXACT_REQUEST_INTERVAL",
                                          "literal": req["ended_utc"], "start_literal": req["started_utc"],
                                          "zone": "Z", "precision": "microsecond", "earliest_utc": req["started_utc"],
                                          "latest_utc": req["ended_utc"], "evidence_document": where,
                                          "evidence_pointer": f"/requests/{i}/ended_utc", "reason": None}})
        kept, duplicates, seen = [], [], set()
        for version in raw:
            split = base.replay_split(version["url"])
            identity = f"wayback:{(split[0] if split else None) or '00000000000000'}:{h_bytes(version['payload'])}"
            if identity in seen:
                duplicates.append({"capture_id": identity,
                                   "receipt_document_sha256": version["receipt_document_sha256"],
                                   "receipt_pointer": version["receipt_pointer"], "request_seq": version["seq"]})
                continue
            seen.add(identity)
            kept.append(version)
        return kept, duplicates

    def key_records(self, key: str, index: int) -> None:
        spec = next(s for s in self.contract["scope"]["keys"] if s["contest_key"] == key)
        row = self.ctx["tranche"][key]
        versions, duplicates = self.union_versions(key, spec)
        captures, assertions = [], []
        for version in versions:
            cap, rows = self.capture(key, spec, version)
            captures.append(cap)
            assertions += rows
        captures.sort(key=lambda c: (c["wayback_timestamp"] or "", c["payload_sha256"]))
        rank = {c["capture_id"]: i for i, c in enumerate(captures)}
        assertions.sort(key=lambda a: (rank[a["capture_id"]], FIELD_LIST.index(a["field"]), a["witness"],
                                       a["witness_span"][0]))
        mine = [(acq_id, r) for acq_id, doc in self.ctx["acquisitions"] for r in doc["requests"]
                if r["contest_key"] == key]
        outcomes = [{"acquisition_identity": acq_id, "acquisition_outcome": doc["outcomes"][key]}
                    for acq_id, doc in self.ctx["acquisitions"] if key in doc["outcomes"]]
        outcome = outcomes[-1]["acquisition_outcome"]
        support = {}
        for field in SUPPORTABLE:
            bounds = sorted(c["clocks"]["archive_capture"]["latest_utc"] for c in captures
                            if c["field_states"][field] == QUAL)
            support[field] = bounds[0] if bounds else None
        supported = [f for f in SUPPORTABLE if support[f]]
        reasons = sorted({r for c in captures for r in c["quarantine_reasons"]})
        if outcome == "CONTROL_REUSED":
            disposition = "CONTROL_REUSED_QUALIFIED" if len(supported) == 6 else "ARCHIVED_VERSION_NOT_QUALIFIED"
        elif captures:
            disposition = "ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS" if len(supported) == 6 else (
                "ARCHIVED_VERSION_QUALIFIED_PARTIAL_FIELDS" if supported else "ARCHIVED_VERSION_NOT_QUALIFIED")
        else:
            disposition = outcome
        if outcome in ("REDIRECT_REFUSED", "REPLAY_REQUEST_FAILED") and captures:
            reasons.append(f"ACQUISITION_{outcome}")
        self.records["dispositions.jsonl"].append({
            "record_type": "archive_disposition", "ord": index, "contest_key": key, "season": row["season"],
            "contest_date": row["contest_date"], "a_key": row["a_key"], "b_key": row["b_key"],
            "classification_pair": row["classification_pair"], "stratum": row["stratum"],
            "selection_role": row["selection_role"], "candidate_url": spec["candidate_url"],
            "game_id_literal": spec["game_id_literal"], "acquisition_outcome": outcome, "disposition": disposition,
            "reasons": sorted(set(reasons)), "request_count": len(mine),
            "metadata_requests": sum(1 for _, r in mine if r["kind"] == "METADATA"),
            "replay_requests": sum(1 for _, r in mine if r["kind"] == "REPLAY"),
            "capture_ids": [c["capture_id"] for c in captures],
            "qualified_capture_ids": [c["capture_id"] for c in captures if c["state"] == "QUALIFIED"],
            "field_support": support, "parent_values": self.ctx["parent"][key]["values"],
            "selection_sources": list(row["selection_sources"]), "acquisition_outcomes": outcomes,
            "duplicate_versions": duplicates})
        for acq_id, req in mine:
            answer = None
            if req["kind"] == "METADATA" and req["http_status"] == 200:
                answer = self.answer(self.raw(req["body_sha256"]), spec["game_id_literal"])
            self.records["requests.jsonl"].append({"record_type": "archive_request", **req,
                                                   "body_path": f"raw/sha256/{req['body_sha256']}"
                                                   if req["body_sha256"] else None, "metadata_answer": answer,
                                                   "acquisition_identity": acq_id})
        self.records["captures.jsonl"] += captures
        self.records["assertions.jsonl"] += assertions


def _parent(db: Path, keys: list[str], rule: str) -> tuple[dict[str, Any], bool]:
    conn = sqlite3.connect("file:" + str(db.resolve()).replace("\\", "/") + "?mode=ro", uri=True)
    parent, single = {}, True
    for key in keys:
        found = conn.execute("SELECT record, assertions, lineage FROM contests WHERE contest_key = ?",
                             (key,)).fetchone()
        if found is None:
            single = False
            continue
        rec = json.loads(found[0])
        seen: dict[str, set[str]] = {}
        values: dict[str, Any] = {}
        for line in zlib.decompress(found[1]).decode("utf-8").splitlines():
            item = json.loads(line)
            values.setdefault(item["field"], item["parent_value"])
            seen.setdefault(item["field"], set()).add(json.dumps(item["parent_value"], sort_keys=True))
        single &= set(seen) == set(FIELD_LIST) and all(len(v) == 1 for v in seen.values())
        lineage = [json.loads(x) for x in zlib.decompress(found[2]).decode("utf-8").splitlines()]
        parent[key] = {"record": rec, "values": {f: values.get(f) for f in FIELD_LIST},
                       "teams": base.team_sources(rec, lineage, rule)}
    conn.close()
    return parent, single


def verify_inputs(contract: dict[str, Any], args: argparse.Namespace, report: Any) -> dict[str, Any]:
    """The parent, the issued tranche and cohort bytes, the union rebuilt here from both, the Cycle 43 bindings and
    the retained control."""
    ctx: dict[str, Any] = {"expansion": True}
    db = Path(args.source_database)
    pop_root = db.resolve().parent.parent.parent
    manifest = pop_root.parent.parent / "manifests" / pop_root.name / "sha256" / db.resolve().parent.name / \
        "run_manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    ident = doc["identity_document"]
    binding = contract["parent_binding"]["source_time"]
    db_sha = h_file(db)
    report.check("parent_source_time_identity_bound", h_bytes(cjson(ident)) == db.resolve().parent.name ==
                 doc["identity"] == binding["database_identity"] and ident["outputs"]["national_source_time.sqlite"]
                 == db_sha == binding["sqlite_sha256"] and ident["content_identity"] == binding["content_identity"]
                 and ident["contract_sha256"] == binding["contract_sha256"], {"identity": doc["identity"]})
    ctx["parent_binding"] = {"source_time": {"database_identity": doc["identity"], "sqlite_sha256": db_sha,
                                             "content_identity": ident["content_identity"],
                                             "contract_sha256": ident["contract_sha256"]}}
    scope = contract["scope"]
    tranche_raw, cohort_raw = Path(args.tranche).read_bytes(), Path(args.cohort).read_bytes()
    tranche, cohort = json.loads(tranche_raw.decode("utf-8")), json.loads(cohort_raw.decode("utf-8"))
    trows, crows = tranche["selected"], cohort["selected"]
    tkeys, ckeys = [r["contest_key"] for r in trows], [r["contest_key"] for r in crows]
    union = tkeys + [k for k in ckeys if k not in set(tkeys)]
    report.check("tranche_bound_and_complete", h_bytes(tranche_raw) == scope["tranche_sha256"] and
                 len(tkeys) == len(set(tkeys)) == scope["tranche_count"] == tranche["count"], {"keys": len(tkeys)})
    report.check("cohort_bound_and_complete", h_bytes(cohort_raw) == scope["cohort_sha256"] and
                 len(ckeys) == len(set(ckeys)) == scope["cohort_count"] == cohort["counts"]["new_query_keys"] and
                 ckeys == scope["cohort_keys"], {"keys": len(ckeys)})
    report.check("union_rebuilt_from_tranche_and_cohort", union == [k["contest_key"] for k in scope["keys"]] and
                 len(union) == scope["union_count"] and [k for k in ckeys if k in set(tkeys)] == scope["overlap_keys"],
                 {"union": len(union), "overlap": [k for k in ckeys if k in set(tkeys)]})
    tby, cby = {r["contest_key"]: r for r in trows}, {r["contest_key"]: r for r in crows}
    spec_ok = True
    for spec in scope["keys"]:
        key = spec["contest_key"]
        t, c = tby.get(key), cby.get(key)
        url = (t or c)["candidate_espn_url"]
        want = {"contest_key": key,
                "selection_sources": [n for n, r in (("TRANCHE_28", t), ("COHORT_70", c)) if r is not None],
                "selection_role": t["selection_role"] if t else COHORT_ROLE,
                "stratum": t["stratum"] if t else COHORT_STRATUM, "candidate_url": url,
                "game_id_literal": url.rsplit("/", 1)[-1],
                "retained_probe_1_timestamp": t["metadata_probe_timestamp"] if t else None,
                "expansion_probe_timestamps": c["metadata_probe_timestamps"] if c else None}
        spec_ok &= spec == want and (c is None or (c["candidate_espn_url"] == url and
                                                   bool(c.get("already_in_original_tranche")) == (t is not None)))
    report.check("declared_union_specs_equal_tranche_and_cohort_rows", spec_ok)
    bindings_raw = Path(args.source_bindings).read_bytes()
    bindings = json.loads(bindings_raw.decode("utf-8"))
    report.check("bindings_bound", h_bytes(bindings_raw) == contract["parent_binding"]["source_bindings"]["sha256"]
                 and bindings["source_time_database"]["sha256"] == db_sha and
                 bindings["tranche"]["sha256"] == h_bytes(tranche_raw) and
                 bindings["expansion_cohort"]["sha256"] == h_bytes(cohort_raw) and
                 bindings["control"]["sha256"] == contract["parent_binding"]["route_control"]["sha256"] and
                 bindings["prior_archive_acquisition_identity"] ==
                 contract["parent_binding"]["retained_acquisition"]["identity"])
    route_path = Path(bindings["control"]["path"])
    route_raw = route_path.read_bytes()
    spec = contract["parent_binding"]["route_control"]
    receipt_raw = (route_path.parent / spec["raw_receipt_document"]).read_bytes()
    payload = (route_path.parent / spec["raw_payload"]).read_bytes()
    route = json.loads(route_raw.decode("utf-8"))
    report.check("control_bytes_bound", h_bytes(route_raw) == spec["sha256"] and
                 h_bytes(receipt_raw) == spec["raw_receipt_sha256"] and h_bytes(payload) == spec["raw_payload_sha256"]
                 and route["conservative_upper_bound"] == spec["conservative_upper_bound"])
    ctx.update(control_route_raw=route_raw, control_receipt_raw=receipt_raw, control_payload=payload,
               control_receipt=json.loads(receipt_raw.decode("utf-8")), control_route=route,
               control_receipt_sha=h_bytes(receipt_raw))
    rule = (contract.get("participant_mapping") or {}).get("rule", "")
    parent, single = _parent(db, union, rule)
    ctx["parent"] = parent
    report.check("parent_values_single_per_field", single and len(parent) == len(union))
    report.check("contract_is_the_bat715_expansion_without_numeric_identity_and_with_capture_quarantine",
                 (contract.get("schema_version"), contract.get("contract_id")) == ("1.0.0", EXPANSION_CONTRACT_ID) and
                 (contract.get("participant_mapping") or {}).get("numeric_identifier_equality") == "NEVER_AUTHORITY"
                 and bool(rule) and "quarantines the whole capture" in str(
                     (contract.get("participant_mapping") or {}).get("capture_quarantine")))
    ctx["participant_source_states"] = {k: p["teams"]["state"] for k, p in parent.items()}
    report.check("tranche_rows_equal_parent", all(
        (tby[k]["a_key"], tby[k]["b_key"], tby[k]["contest_date"], tby[k]["a_points"], tby[k]["b_points"]) ==
        (parent[k]["record"]["a_key"], parent[k]["record"]["b_key"], parent[k]["record"]["contest_date"],
         parent[k]["values"]["a_points"], parent[k]["values"]["b_points"]) for k in tkeys if k in parent))
    report.check("cohort_rows_equal_parent", all(
        (cby[k]["a_key"], cby[k]["b_key"], cby[k]["contest_date"], cby[k]["cfbd_game_id"]["value"]) ==
        (parent[k]["record"]["a_key"], parent[k]["record"]["b_key"], parent[k]["record"]["contest_date"],
         parent[k]["record"]["cfbd_game_id"]["value"]) for k in ckeys if k in parent))
    rows = {}
    for key in union:
        t, rec = tby.get(key), parent.get(key, {}).get("record") or {}
        rows[key] = {"contest_key": key, "season": t["season"] if t else rec.get("season"),
                     "contest_date": (t or cby[key])["contest_date"], "a_key": (t or cby[key])["a_key"],
                     "b_key": (t or cby[key])["b_key"], "classification_pair": t["classification_pair"] if t else None,
                     "stratum": t["stratum"] if t else COHORT_STRATUM,
                     "selection_role": t["selection_role"] if t else COHORT_ROLE,
                     "selection_sources": [n for n, r in (("TRANCHE_28", t), ("COHORT_70", cby.get(key)))
                                           if r is not None]}
    ctx.update(tranche=rows, cohort=cby, cohort_targets=cohort.get("targets") or [],
               retained_root=Path(args.retained_root) if getattr(args, "retained_root", None) else None,
               retained_contract=Path(args.retained_contract) if getattr(args, "retained_contract", None) else None)
    return ctx


def verify_acquisition(contract: dict[str, Any], ctx: dict[str, Any], content: dict[str, Any], report: Any) -> None:
    """Both receipt documents: the retained V1.2 acquisition (policy recomputed from the committed V1.2 contract; its
    copy byte-identical with the read-only V1.2 root) and the expansion acquisition (journal, probes, limits)."""
    out = ctx["out"]
    spec = contract["parent_binding"]["retained_acquisition"]
    rid = spec["identity"]
    rdata = (out / "acquisition" / "sha256" / rid / "acquisition.json").read_bytes()
    rdoc = json.loads(rdata.decode("utf-8"))
    v12_raw = Path(ctx.get("retained_contract") or V12_CONTRACT).read_bytes()
    v12 = json.loads(v12_raw.decode("utf-8"))
    rpolicy = h_bytes(cjson({"acquisition": v12["acquisition"], "tranche_sha256": contract["scope"]["tranche_sha256"]}))
    tkeys = [k for k, row in ctx["tranche"].items() if "TRANCHE_28" in row["selection_sources"]]
    report.check("retained_acquisition_bound", h_bytes(rdata) == rid and h_bytes(v12_raw) == spec["contract_sha256"]
                 and rdoc["policy_id"] == rpolicy == spec["policy_id"] and rdoc["contract_id"] == spec["contract_id"]
                 and rdoc["tranche_sha256"] == contract["scope"]["tranche_sha256"] and rdoc["keys"] == tkeys and
                 len(rdoc["requests"]) == spec["requests"], {"policy": rpolicy})
    source = ctx.get("retained_root") or out.parent / "national_archived_publication_2019"
    copied = [f"acquisition/sha256/{rid}/acquisition.json"] + [
        f"acquisition/journal/{spec['policy_id']}/{n}" for n in sorted(spec["journal_files"])] + sorted(
        {f"raw/sha256/{r['body_sha256']}" for r in rdoc["requests"] if r.get("body_sha256")} |
        {f"raw/sha256/{rdoc['control'][k]}" for k in ("payload_sha256", "raw_receipt_sha256",
                                                      "route_qualification_sha256")})
    different = [rel for rel in copied if not (source / rel).is_file() or not (out / rel).is_file() or
                 (source / rel).read_bytes() != (out / rel).read_bytes()]
    journal_ok = all(h_file(out / "acquisition" / "journal" / spec["policy_id"] / n) == s
                     for n, s in spec["journal_files"].items())
    report.check("retained_copy_byte_identical_with_the_v1_2_root", source.is_dir() and not different and journal_ok,
                 {"source": str(source), "files": len(copied), "different": different[:5]})
    acq_id = content["acquisition_identity"]
    data = (out / "acquisition" / "sha256" / acq_id / "acquisition.json").read_bytes()
    acq = json.loads(data.decode("utf-8"))
    policy = h_bytes(cjson({"acquisition": contract["acquisition"],
                            "tranche_sha256": contract["scope"]["cohort_sha256"]}))
    report.check("acquisition_document_bound", h_bytes(data) == acq_id and acq["policy_id"] == policy ==
                 content["acquisition_policy_id"] and acq["tranche_sha256"] == contract["scope"]["cohort_sha256"]
                 and acq["keys"] == contract["scope"]["cohort_keys"] and acq["contract_id"] == EXPANSION_CONTRACT_ID)
    report.check("content_names_both_acquisitions_in_order", content.get("acquisitions") == [
        {"acquisition_identity": rid, "policy_id": spec["policy_id"], "origin": RETAINED_ORIGIN},
        {"acquisition_identity": acq_id, "policy_id": policy, "origin": EXPANSION_ORIGIN}])
    journal = out / "acquisition" / "journal" / policy / "journal.jsonl"
    lines = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines() if x]
    intents = [x for x in lines if x["type"] == "INTENT"]
    results = {x["seq"]: x["request"] for x in lines if x["type"] == "RESULT"}
    rebuilt = [results.get(i["seq"]) or {"seq": i["seq"], "outcome": "INTERRUPTED_UNKNOWN"} for i in intents]
    finals = [x for x in lines if x["type"] == "FINALIZED"]
    report.check("journal_reproduces_requests", lines[0]["type"] == "HEADER" and
                 [r["seq"] for r in rebuilt] == list(range(1, len(rebuilt) + 1)) and
                 [cjson(r) for r in rebuilt] == [cjson(r) for r in acq["requests"]] and
                 bool(finals) and finals[-1]["acquisition_identity"] == acq_id,
                 {"intents": len(intents), "results": len(results)})
    limits = contract["acquisition"]["limits"]
    per_key_ok = host_ok = purpose_ok = probe_ok = True
    specs = {k["contest_key"]: k for k in contract["scope"]["keys"]}
    for key in contract["scope"]["cohort_keys"]:
        kspec = specs[key]
        first, second = kspec["expansion_probe_timestamps"]
        mine = [r for r in acq["requests"] if r["contest_key"] == key]
        metas = [r for r in mine if r["kind"] == "METADATA"]
        reps = [r for r in mine if r["kind"] == "REPLAY"]
        if len(metas) > limits["metadata_requests_per_key"] or len(reps) > limits["replay_requests_per_key"]:
            per_key_ok = False
        for r in metas:
            m = re.fullmatch(r"https://archive\.org/wayback/available\?url=([^&]+)&timestamp=(\d{14})", r["url"])
            if not m or unquote(m.group(1)) != kspec["candidate_url"]:
                host_ok = False
                continue
            stamp = m.group(2)
            if r["purpose"] not in ("PROBE_1", "PROBE_2", "RETRY"):
                purpose_ok = False
            if (r["purpose"] in ("PROBE_1", "RETRY") and stamp != first) or \
                    (r["purpose"] == "PROBE_2" and (stamp != second or second == first)):
                probe_ok = False
        if metas and metas[0]["purpose"] != "PROBE_1":
            probe_ok = False
        for r in reps:
            split = base.replay_split(r["url"])
            if not split or not base.is_game_url(split[1], kspec["game_id_literal"]):
                host_ok = False
            if r["purpose"] not in ("CAPTURE_1", "CAPTURE_2", "RETRY", "REDIRECT_HOP"):
                purpose_ok = False
    report.check("per_key_and_total_limits_held",
                 per_key_ok and len(acq["requests"]) <= limits["total_requests"] <= 320,
                 {"requests": len(acq["requests"])})
    report.check("only_granted_archive_urls_requested", host_ok)
    report.check("request_purposes_declared", purpose_ok)
    report.check("probe_timestamps_are_the_declared_ones", probe_ok)
    starts = [dt.datetime.strptime(r["started_utc"], "%Y-%m-%dT%H:%M:%S.%fZ") for r in acq["requests"]]
    report.check("request_times_recorded_and_ordered", all(b > a for a, b in zip(starts, starts[1:])) and all(
        r["ended_utc"] is None or r["ended_utc"] >= r["started_utc"] for r in acq["requests"]))
    gaps = [{"from_seq": a["seq"], "to_seq": b["seq"], "gap_seconds": round((y - x).total_seconds(), 6)}
            for a, b, x, y in zip(acq["requests"], acq["requests"][1:], starts, starts[1:])]
    short = [g for g in gaps if g["gap_seconds"] < limits["min_seconds_between_request_starts"]]
    statuses: dict[str, int] = {}
    for r in acq["requests"]:
        statuses[str(r["http_status"])] = statuses.get(str(r["http_status"]), 0) + 1
    ctx["grant_conditions"] = {
        "request_start_spacing": {
            "declared_min_seconds": limits["min_seconds_between_request_starts"], "intervals": len(gaps),
            "recorded_min_gap_seconds": min((g["gap_seconds"] for g in gaps), default=None),
            "intervals_below_declared": short, "state": "DEVIATION_RECORDED" if short else "HELD"},
        "total_requests": {"declared_max": limits["total_requests"], "actual": len(acq["requests"]),
                           "state": "HELD" if len(acq["requests"]) <= limits["total_requests"] else "EXCEEDED"},
        "per_key_requests": {"state": "HELD" if per_key_ok else "EXCEEDED"},
        "hosts": {"state": "HELD" if host_ok else "VIOLATED"}, "http_statuses": statuses}
    bodies_ok = True
    for doc_ in (rdoc, acq):
        for r in doc_["requests"]:
            if r.get("body_sha256"):
                raw = out / "raw" / "sha256" / r["body_sha256"]
                bodies_ok &= raw.is_file() and h_file(raw) == r["body_sha256"] and raw.stat().st_size == r["body_bytes"]
    report.check("every_raw_body_retained_unchanged", bodies_ok)
    controls_ok = True
    for doc_ in (rdoc, acq):
        ctl = doc_["control"]
        controls_ok &= ctl["requests"] == 0 and ctl["payload_sha256"] == h_bytes(ctx["control_payload"]) and \
            ctl["raw_receipt_sha256"] == h_bytes(ctx["control_receipt_raw"]) and \
            ctl["route_qualification_sha256"] == h_bytes(ctx["control_route_raw"])
    report.check("control_reused_with_zero_requests", controls_ok)
    ctx.update(acquisitions=[(rid, rdoc), (acq_id, acq)], acquisition=acq, acquisition_id=acq_id,
               retained_acquisition_id=rid)


def union_tamper_cases(expected: Expected, delivered: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Coordinated tampers of the union fields; each must be rejected by the field-by-field comparison."""
    out: list[dict[str, Any]] = []
    acq_ids = [a for a, _ in expected.ctx["acquisitions"]]

    def run(name: str, mutate) -> None:
        copy_ = copy.deepcopy(delivered)
        applied = bool(mutate(copy_))
        out.append({"case": name, "applied": applied,
                    "rejected": (not clean(compare(expected, copy_))) if applied else None})

    def edit(name: str, pred, change):
        def mutate(d):
            item = next((x for x in d[name] if pred(x)), None)
            if item is None:
                return False
            change(item)
            return True
        return mutate
    failed = ("METADATA_REQUEST_FAILED", "NO_ARCHIVE_CAPTURE_REPORTED", "REPLAY_REQUEST_FAILED", "REDIRECT_REFUSED",
              "RETAINED_VERSION_REUSED")
    run("union_selection_sources_forged", edit("dispositions.jsonl", lambda x: x["selection_sources"] == ["COHORT_70"],
                                               lambda x: x.update(selection_sources=["TRANCHE_28"])))
    run("union_acquisition_outcome_history_rewritten", edit("dispositions.jsonl", lambda x: len(
        x["acquisition_outcomes"]) == 2, lambda x: x.update(acquisition_outcomes=x["acquisition_outcomes"][-1:])))
    run("union_failed_outcome_relabelled_captured", edit("dispositions.jsonl", lambda x: x["acquisition_outcome"]
                                                         in failed, lambda x: x.update(
        acquisition_outcome="CAPTURED", acquisition_outcomes=[dict(o, acquisition_outcome="CAPTURED")
                                                              for o in x["acquisition_outcomes"]])))
    run("union_request_moved_to_the_other_acquisition", edit("requests.jsonl", lambda r: r["acquisition_identity"]
                                                             == acq_ids[-1], lambda r: r.update(
        acquisition_identity=acq_ids[0])))
    run("union_cohort_key_classified", edit("dispositions.jsonl", lambda x: x["classification_pair"] is None,
                                            lambda x: x.update(classification_pair="FBS-FBS")))
    run("union_duplicate_version_hidden", edit("dispositions.jsonl", lambda x: True, lambda x: x.update(
        duplicate_versions=[{"capture_id": "wayback:20190101000000:" + "0" * 64, "receipt_document_sha256": acq_ids[-1],
                             "receipt_pointer": "/requests/0", "request_seq": 1}])))

    def drop_retained(d: dict[str, list[dict[str, Any]]]) -> bool:
        kept = [r for r in d["requests.jsonl"] if r["acquisition_identity"] != acq_ids[0]]
        if len(kept) == len(d["requests.jsonl"]):
            return False
        d["requests.jsonl"] = kept
        return True
    run("union_retained_requests_dropped", drop_retained)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("contract", "source-database", "source-bindings", "tranche", "cohort", "manifest", "report"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--retained-root", type=Path, default=None,
                        help="the read-only V1.2 canonical root the retained copy must equal "
                             "(default: <canonical>/national_archived_publication_2019)")
    parser.add_argument("--retained-contract", type=Path, default=None,
                        help="the contract whose acquisition section defines the retained policy (default: the "
                             "committed V1.2 contract; its bytes must hash to the bound sha256)")
    parser.add_argument("--skip-consumer", action="store_true", help="test hook: no consumer subprocess")
    args = parser.parse_args(argv)
    if args.report.exists():
        raise SystemExit("the report path already exists (written once)")
    report = Report()
    report.check("accepted_archive_oracle_bytes_bound", h_file(ACCEPTED_ORACLE) == ACCEPTED_ORACLE_SHA256)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    ctx = verify_inputs(contract, args, report)
    manifest = Path(args.manifest)
    ctx["out"] = manifest.parent.parent.parent.parent.parent / "canonical" / manifest.parent.parent.parent.name
    content_doc = json.loads(manifest.read_text(encoding="utf-8"))["identity_document"]
    verify_acquisition(contract, ctx, content_doc, report)
    delivered = read_delivered(manifest, ctx, report)
    report.check("content_binds_contract_parent_tranche_and_cohort", delivered["content"]["contract_sha256"] == h_bytes(
        args.contract.read_bytes()) and delivered["content"]["parent"] == ctx["parent_binding"] and
        delivered["content"]["tranche_sha256"] == contract["scope"]["tranche_sha256"] and
        delivered["content"].get("cohort_sha256") == contract["scope"]["cohort_sha256"])
    expected = Expected(contract, ctx)
    expected.build()
    result = compare(expected, delivered["records"])
    report.check("every_record_reconstructed_independently", clean(result), result)
    want = [c["capture_id"] for c in expected.records["captures.jsonl"]]
    have = [c["capture_id"] for c in delivered["records"]["captures.jsonl"]]
    report.check("capture_collection_equals_control_plus_receipted_replays_of_both_acquisitions",
                 want == have and len(set(have)) == len(have),
                 {"expected": len(want), "delivered": len(have), "missing": sorted(set(want) - set(have))[:5],
                  "extra": sorted(set(have) - set(want))[:5]})
    report.check("reconstructed_payloads_hash_to_delivered_semantics", all(
        h_bytes(lines_of(expected.records[n])) == delivered["content"]["semantic_outputs"][n] for n in PAYLOAD_NAMES))
    if args.skip_consumer:
        decisions = {"skipped": True}
    else:
        cutoffs = list(base.PROBE_CUTOFFS) + sorted({t["cutoff_exclusive"] for t in ctx["cohort_targets"]})
        saved = base.PROBE_CUTOFFS
        base.PROBE_CUTOFFS = cutoffs
        try:
            decisions = base.decision_checks(args, delivered, expected, report)
        finally:
            base.PROBE_CUTOFFS = saved
    tampers = base.tamper_cases(expected, delivered["records"]) + union_tamper_cases(expected, delivered["records"])
    applied = [t for t in tampers if t["applied"]]
    report.check("every_tamper_case_rejected", len(applied) >= 10 and all(t["rejected"] for t in applied),
                 {"applied": len(applied), "not_applicable": [t["case"] for t in tampers if not t["applied"]],
                  "not_rejected": [t["case"] for t in applied if not t["rejected"]]})
    probe_view = copy.deepcopy(contract)
    for spec in probe_view["scope"]["keys"]:
        spec["probe_1_timestamp"] = spec["retained_probe_1_timestamp"] or spec["expansion_probe_timestamps"][0]
    viewer = Expected(probe_view, ctx)
    viewer.records = expected.records
    oracle = base.challenges(viewer, delivered["records"], ctx)
    second = {s["contest_key"]: set(s["expansion_probe_timestamps"] or []) for s in contract["scope"]["keys"]}
    oracle.append({"challenge": "expansion_probe_timestamps_never_used_as_bounds", "as_expected": all(
        c["wayback_timestamp"] not in second[c["contest_key"]] or c["memento_datetime_literal"] is not None
        for c in delivered["records"]["captures.jsonl"])})
    report.check("oracle_self_challenges_as_expected", all(c["as_expected"] for c in oracle),
                 [c["challenge"] for c in oracle if not c["as_expected"]])
    tally: dict[str, int] = {}
    for d in delivered["records"]["dispositions.jsonl"]:
        tally[d["disposition"]] = tally.get(d["disposition"], 0) + 1
    outcomes: dict[str, int] = {}
    for d in delivered["records"]["dispositions.jsonl"]:
        outcomes[d["acquisition_outcome"]] = outcomes.get(d["acquisition_outcome"], 0) + 1
    fields = {f: sum(1 for d in delivered["records"]["dispositions.jsonl"] if d["field_support"][f])
              for f in SUPPORTABLE}
    failed = report.failed()
    doc = {"tool": "tools/validate_national_archived_publication_expansion.py", "tool_sha256": h_file(Path(__file__)),
           "accepted_oracle": {"path": str(ACCEPTED_ORACLE), "sha256": ACCEPTED_ORACLE_SHA256},
           "result": "PASS" if not failed else "FAIL", "failed_checks": failed, "checks": report.checks,
           "content_identity": delivered["content_identity"], "database_identity": delivered["database_identity"],
           "acquisition_identity": ctx["acquisition_id"],
           "retained_acquisition_identity": ctx["retained_acquisition_id"],
           "counts": {"union_keys": len(contract["scope"]["keys"]), "dispositions": tally,
                      "acquisition_outcomes": outcomes,
                      "requests": sum(len(d["requests"]) for _, d in ctx["acquisitions"]),
                      "new_requests_this_acquisition": len(ctx["acquisition"]["requests"]),
                      "captures": len(delivered["records"]["captures.jsonl"]),
                      "qualified_captures": sum(1 for c in delivered["records"]["captures.jsonl"]
                                                if c["state"] == "QUALIFIED"),
                      "assertions": len(delivered["records"]["assertions.jsonl"]),
                      "keys_with_field_support": fields, "strata": base.strata(delivered["records"]),
                      "participant_maps": {
                          "qualified": sum(1 for c in delivered["records"]["captures.jsonl"]
                                           if c["participant_mapping"]["state"] == "QUALIFIED"),
                          "unresolved": sorted({c["participant_mapping"]["reason"]
                                                for c in delivered["records"]["captures.jsonl"]
                                                if c["participant_mapping"]["state"] != "QUALIFIED"}),
                          "source_states": ctx.get("participant_source_states")}},
           "grant_conditions": ctx.get("grant_conditions"), "decisions": decisions, "tamper_cases": tampers,
           "oracle_challenges": oracle,
           "independence": "standard library only; no producer, query or project import; the accepted Cycle 41 oracle "
                           "is loaded by path after its bytes hash to the accepted value; the consumer is exercised "
                           "only as a subprocess and compared with this tool's own decisions",
           "limits": ["a bounded 97-key 2019 union (28-key tranche plus 70-key missing-prior cohort), not a national "
                      "or seasonal audit",
                      "archive captures are upper bounds for the exact witnessed versions, never first publication",
                      "capture times are the archive's receipts; this offline tool cannot re-query the archive",
                      "a request answered HTTP 429 is evidence of refusal, not of absence of an archived version",
                      "a coordinated forgery that rewrites raw bytes, receipts and every hash is detectable only "
                      "against the committed gate identities and the manager's independent control receipt"],
           "observed_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"result": doc["result"], "failed_checks": failed, "counts": doc["counts"]}, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
