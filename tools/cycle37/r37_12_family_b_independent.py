"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-12 / R36-12: an independent reconstruction of the composed Family B
successor's scientific fields, from raw bytes, for the composed probe.

The composed probe runs the real consumer validators. Those validators get
their verdict by comparing a committed artifact with the producer's own
reconstruction, so a defect shared by both halves of the producer would pass.
This file recomputes what acceptance depends on without importing any
aggie_analytics code:

* the upstream rejection ledger: the historical and active rejection sets,
  the supersession rows (each joined to its admitted successor game), the
  row-gap URLs, and the ledger identity;
* the downstream union: its admitted and rejected URL lists, its counts
  (rejection counts are taken from list LENGTHS, and the declared count
  fields are then checked against them), and the union identity;
* that no active rejected URL appears anywhere in the structured-row corpus
  child files. This is a raw byte search over every file, not the
  producer's per-domain ``source_url`` parse;
* that both gate identities recompute from the gate's own fields.

An identity is defined by its hashing convention (canonical JSON, then
SHA-256), so recomputing one has to follow that convention and the field
list the contract declares. What does NOT depend on the producer is the
derivation of each field from raw inputs, and the set, join, length and leak
checks, which are written differently here.

It also compares the predecessor artifacts in the canonical lake (read-only)
with the candidate, so any identity that changed is explained from content.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

UPSTREAM_GATE = "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json"
UPSTREAM_CONTRACT = "configs/tamu_official_1998_2009_rejection_integrity_contract.json"
UNION_1996_GATE = "artifacts/data_lake/tamu_official_gamebook_union_1996_expanded_gate.json"
BAT637_GATE = "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json"
CORPUS_GATE = "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_gate.json"
STRUCTURED_GATES = {
    1996: "artifacts/data_lake/tamu_official_1996_structured_domains_gate.json",
    1997: "artifacts/data_lake/tamu_official_1997_structured_domains_gate.json",
}
DOWNSTREAM_GATE = "artifacts/data_lake/tamu_official_gamebook_union_1998_rejection_complete_gate.json"
LEDGER_ROOT = "features/tamu_official_1998_2009_rejection_integrity/sha256"
UNION_1996_ROOT = "features/tamu_official_gamebook_union_1996_expanded/sha256"
UNION_ROOT = "features/tamu_official_gamebook_union_1998_rejection_complete/sha256"
CORPUS_ROOT = "features/tamu_official_1998_2009_structured_row_corpus/sha256"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def content_hash(value: Any) -> str:
    """The declared content-identity convention: canonical JSON, SHA-256."""

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def gate_hash(gate: dict[str, Any]) -> str:
    """The declared gate-identity convention: ASCII canonical JSON without the field."""

    body = {key: value for key, value in gate.items() if key != "gate_identity"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def urls(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row.get("url") or "") for row in rows]


def upstream(repo: Path, data: Path) -> dict[str, Any]:
    union_gate = read(repo / UNION_1996_GATE)
    union = read(data / UNION_1996_ROOT / union_gate["union_identity"] / "union_manifest.json")
    historical = list(union.get("complete_rejection_ledger") or [])
    active = list(union.get("active_rejections") or [])
    admitted = {url: game for url, game in zip(urls(union["enriched_official_games"]), union["enriched_official_games"])}
    gap_urls = list(union.get("admitted_row_gap_urls") or [])
    contract = read(repo / UPSTREAM_CONTRACT)
    structured = {season: read(repo / rel)["payload_identity"] for season, rel in STRUCTURED_GATES.items()}
    corpus_gate = read(repo / CORPUS_GATE)
    checks: dict[str, bool] = {
        "historical_urls_unique": len(set(urls(historical))) == len(historical),
        "active_urls_unique": len(set(urls(active))) == len(active),
        "active_is_subset_of_historical": set(urls(active)) <= set(urls(historical)),
        "no_active_rejection_is_admitted": not (set(urls(active)) & set(admitted)),
        "every_row_gap_url_is_admitted_and_not_active": all(u in admitted and u not in set(urls(active)) for u in gap_urls),
    }
    supersessions, unjoined = [], []
    for row in historical:
        if not row.get("superseded"):
            continue
        game = admitted.get(str(row.get("url") or ""))
        if game is None or int(game.get("source_season") or 0) not in STRUCTURED_GATES:
            unjoined.append(row.get("url"))
            continue
        season = int(game["source_season"])
        supersessions.append({
            "old_rejection_identity": content_hash({key: row.get(key) for key in (
                "url", "source_sha256", "source_season", "rejection_source")}),
            "url": row["url"],
            "new_normalized_game_identity": content_hash({key: game.get(key) for key in (
                "url", "calendar_date", "source_sha256", "source_season")}),
            "new_structured_payload_identity": structured[season],
            "new_union_identity": union_gate["union_identity"],
            "material_merge_sha": contract.get("supersession_material_merge_sha"),
            "reason_code": "SUPERSEDED_BY_VERIFIED_LEGACY_H2_FORMAT_RECOVERY",
        })
    supersessions.sort(key=lambda row: row["url"])
    checks["every_supersession_joins_an_admitted_1996_or_1997_game"] = not unjoined
    checks["no_superseded_url_is_still_active"] = not ({r["url"] for r in supersessions} & set(urls(active)))
    ledger_identity = content_hash({
        "predecessor_union_identity": union_gate["union_identity"],
        "predecessor_corpus_identity": corpus_gate["dataset_identity"],
        "historical_rejections": historical,
        "active_rejections": active,
        "supersessions": supersessions,
        "admitted_row_gap_urls": gap_urls,
    })
    committed_gate = read(repo / UPSTREAM_GATE)
    ledger_path = data / LEDGER_ROOT / ledger_identity / "rejection_ledger.json"
    ledger = read(ledger_path) if ledger_path.is_file() else {}
    checks.update({
        "ledger_child_exists_at_the_recomputed_identity": ledger_path.is_file(),
        "ledger_states_the_recomputed_identity": ledger.get("ledger_identity") == ledger_identity,
        "ledger_lists_equal_the_raw_union_lists": (
            ledger.get("complete_rejection_ledger") == historical
            and ledger.get("active_rejections") == active
            and ledger.get("admitted_row_gap_urls") == gap_urls),
        "ledger_supersessions_equal_the_recomputed_rows": ledger.get("supersessions") == supersessions,
        "ledger_count_fields_equal_list_lengths": (
            ledger.get("complete_rejection_count") == len(historical)
            and ledger.get("active_rejection_count") == len(active)),
        "committed_gate_names_the_recomputed_ledger": committed_gate.get("ledger_identity") == ledger_identity,
        "committed_gate_identity_recomputes": committed_gate.get("gate_identity") == gate_hash(committed_gate),
        "committed_gate_counts_equal_list_lengths": (
            committed_gate.get("complete_rejection_count") == len(historical)
            and committed_gate.get("active_rejection_count") == len(active)
            and committed_gate.get("superseded_rejection_count") == len(supersessions)),
    })
    return {"ledger_identity": ledger_identity, "gate_identity": committed_gate.get("gate_identity"),
            "historical_rejections": len(historical), "active_rejections": len(active),
            "supersessions": len(supersessions), "row_gap_urls": gap_urls, "active_urls": urls(active),
            "admitted_sample_urls": sorted(u for u, g in admitted.items() if int(g.get("source_season") or 0) >= 1998)[:3],
            "ledger_path": str(ledger_path), "checks": checks}


def leak_scan(data: Path, active_urls: list[str]) -> dict[str, Any]:
    """Raw byte search for every active rejected URL in every corpus child file."""

    pattern = re.compile(b"|".join(re.escape(u.encode("utf-8")) for u in active_urls if u))
    per_file: dict[str, int] = {}
    for path in sorted((data / CORPUS_ROOT).rglob("*.jsonl")):
        per_file[path.name] = sum(1 for _ in pattern.finditer(path.read_bytes()))
    return {"files_scanned": len(per_file), "occurrences_by_file": per_file,
            "no_active_rejected_url_anywhere_in_the_corpus": sum(per_file.values()) == 0 and bool(per_file)}


def downstream(repo: Path, data: Path, ledger_identity: str) -> dict[str, Any]:
    bat637 = read(repo / BAT637_GATE)
    ledger = read(data / LEDGER_ROOT / ledger_identity / "rejection_ledger.json")
    games = list(bat637.get("enriched_official_games") or [])
    rejected = list(ledger.get("complete_rejection_ledger") or [])
    active = list(ledger.get("active_rejections") or [])
    counts = dict(bat637.get("counts") or {})
    counts["union_captured_games"] = int(counts.get("union_captured_games") or 0)
    counts["union_target_games"] = int(counts.get("union_target_games") or counts["union_captured_games"])
    counts["rejected_urls_complete"] = len(rejected)
    counts["unmatched_rejected"] = len(active)
    counts["ncaa_contest_ids_created"] = 0
    union_identity = content_hash({
        "predecessor_union_identity": bat637.get("union_identity"),
        "rejection_ledger_identity": ledger_identity,
        "admitted_urls": urls(games),
        "rejected_urls": urls(rejected),
        "counts": counts,
    })
    manifest_path = data / UNION_ROOT / union_identity / "union_manifest.json"
    manifest = read(manifest_path) if manifest_path.is_file() else {}
    gate = read(repo / DOWNSTREAM_GATE)
    checks = {
        "union_child_exists_at_the_recomputed_identity": manifest_path.is_file(),
        "manifest_states_the_recomputed_identity": manifest.get("union_identity") == union_identity,
        "manifest_games_equal_the_bat637_games": manifest.get("enriched_official_games") == games,
        "manifest_rejections_equal_the_ledger": manifest.get("complete_rejection_ledger") == rejected,
        "manifest_counts_equal_the_length_derived_counts": manifest.get("counts") == counts,
        "no_active_rejection_is_admitted": not (set(urls(active)) & set(urls(games))),
        "manifest_names_the_ledger_it_was_built_from": manifest.get("rejection_ledger_identity") == ledger_identity,
        "gate_names_the_recomputed_union": gate.get("union_identity") == union_identity,
        "gate_names_the_ledger": gate.get("rejection_ledger_identity") == ledger_identity,
        "gate_identity_recomputes": gate.get("gate_identity") == gate_hash(gate),
        "gate_counts_equal_the_length_derived_counts": gate.get("counts") == counts,
    }
    return {"union_identity": union_identity, "gate_identity": gate.get("gate_identity"),
            "admitted_games": len(games), "rejected_urls": len(rejected), "active_rejections": len(active),
            "counts": counts, "manifest_path": str(manifest_path), "checks": checks}


def _set_diff(before: list[str], after: list[str]) -> dict[str, Any]:
    return {"predecessor": len(before), "candidate": len(after),
            "only_in_predecessor": sorted(set(before) - set(after)),
            "only_in_candidate": sorted(set(after) - set(before)),
            "same_set": set(before) == set(after), "same_order": before == after}


def compare_predecessor(canonical_repo: Path, canonical_data: Path, candidate_data: Path,
                        candidate_ledger: str, candidate_union: str) -> dict[str, Any]:
    """Predecessor (canonical, read-only) against candidate, row by row."""

    pred_gate = read(canonical_repo / UPSTREAM_GATE)
    pred_ledger = read(canonical_data / LEDGER_ROOT / pred_gate["ledger_identity"] / "rejection_ledger.json")
    cand_ledger = read(candidate_data / LEDGER_ROOT / candidate_ledger / "rejection_ledger.json")
    by_url_pred = {r["url"]: r for r in pred_ledger.get("complete_rejection_ledger") or []}
    by_url_cand = {r["url"]: r for r in cand_ledger.get("complete_rejection_ledger") or []}
    changed_rows = sorted(u for u in set(by_url_pred) & set(by_url_cand) if by_url_pred[u] != by_url_cand[u])
    keys_pred, keys_cand = set(pred_ledger), set(cand_ledger)
    upstream_diff = {
        "predecessor_ledger_identity": pred_gate["ledger_identity"],
        "candidate_ledger_identity": candidate_ledger,
        "fields_only_in_predecessor": sorted(keys_pred - keys_cand),
        "fields_only_in_candidate": sorted(keys_cand - keys_pred),
        "fields_whose_value_changed": sorted(k for k in keys_pred & keys_cand if pred_ledger[k] != cand_ledger[k]),
        "historical_rejections": _set_diff(list(by_url_pred), list(by_url_cand)),
        "historical_rows_changed_in_place": changed_rows,
        "active_rejections": _set_diff(urls(pred_ledger.get("active_rejections") or []),
                                       urls(cand_ledger.get("active_rejections") or [])),
        "supersessions_predecessor": len(pred_ledger.get("supersessions") or []),
        "supersessions_candidate": len(cand_ledger.get("supersessions") or []),
    }
    pred_down_gate = read(canonical_repo / DOWNSTREAM_GATE)
    pred_union = read(canonical_data / UNION_ROOT / pred_down_gate["union_identity"] / "union_manifest.json")
    cand_union = read(candidate_data / UNION_ROOT / candidate_union / "union_manifest.json")
    counts_pred, counts_cand = pred_union.get("counts") or {}, cand_union.get("counts") or {}
    downstream_diff = {
        "predecessor_union_identity": pred_down_gate["union_identity"],
        "candidate_union_identity": candidate_union,
        "predecessor_built_on": {"bat637_union": pred_union.get("predecessor_union_identity"),
                                 "bat637_gate": pred_union.get("predecessor_gate_identity"),
                                 "rejection_ledger": pred_union.get("rejection_ledger_identity")},
        "candidate_built_on": {"bat637_union": cand_union.get("predecessor_union_identity"),
                               "bat637_gate": cand_union.get("predecessor_gate_identity"),
                               "rejection_ledger": cand_union.get("rejection_ledger_identity")},
        "admitted_games": _set_diff(urls(pred_union.get("enriched_official_games") or []),
                                    urls(cand_union.get("enriched_official_games") or [])),
        "rejected_urls": _set_diff(urls(pred_union.get("complete_rejection_ledger") or []),
                                   urls(cand_union.get("complete_rejection_ledger") or [])),
        "counts_changed": {k: [counts_pred.get(k), counts_cand.get(k)]
                           for k in sorted(set(counts_pred) | set(counts_cand)) if counts_pred.get(k) != counts_cand.get(k)},
    }
    return {"upstream": upstream_diff, "downstream": downstream_diff}


def run(repo: Path, data: Path, canonical_repo: Path, canonical_data: Path) -> dict[str, Any]:
    up = upstream(repo, data)
    leaks = leak_scan(data, up["active_urls"])
    # The scan must be able to find something, or a zero means nothing:
    # admitted 1998+ games have rows in the corpus.
    leaks["positive_control"] = leak_scan(data, up["admitted_sample_urls"])
    leaks["positive_control_found_admitted_urls"] = not leaks["positive_control"][
        "no_active_rejected_url_anywhere_in_the_corpus"]
    down = downstream(repo, data, up["ledger_identity"])
    comparison = compare_predecessor(canonical_repo, canonical_data, data, up["ledger_identity"], down["union_identity"])
    checks = {**{f"upstream.{k}": v for k, v in up["checks"].items()},
              **{f"downstream.{k}": v for k, v in down["checks"].items()},
              "corpus.no_active_rejected_url_anywhere_in_the_corpus": leaks["no_active_rejected_url_anywhere_in_the_corpus"],
              "corpus.scan_positive_control_finds_admitted_urls": leaks["positive_control_found_admitted_urls"]}
    return {"method": "stdlib only; imports no aggie_analytics code", "upstream": up, "corpus_leak_scan": leaks,
            "downstream": down, "predecessor_comparison": comparison, "checks": checks,
            "failed_checks": sorted(k for k, v in checks.items() if not v), "all_checks_pass": all(checks.values())}
