"""1998-2009 official SRC-014 structured row-corpus successor to BAT-629."""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus import CHILD_FILENAMES
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_1998_2009_structured_row_corpus.v1"
VALIDATION_CONTRACT_VERSION = SCHEMA_VERSION
CONTRACT_RELATIVE = "configs/tamu_official_1998_2009_structured_row_corpus_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_gate.json"
CONTRACT_ID = "BAT-638-TAMU-OFFICIAL-1998-2009-STRUCTURED-ROW-CORPUS-V1"
DECISION_UNIT = "POST-TASK-SRC014-1998-2009-STRUCTURED-ROW-CORPUS-001"
JIRA_KEY = "BAT-638"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1998_2009_STRUCTURED_ROW_CORPUS_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1998_2009_STRUCTURED_ROW_CORPUS"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
FEATURE_ROOT = "features/tamu_official_1998_2009_structured_row_corpus/sha256"
SERIALIZED_DOMAINS = (
    "team_statistics",
    "individual_player_statistics",
    "drives",
    "play_by_play",
    "scoring_summary",
)
PINNED_PREDECESSOR_DATASET_IDENTITY = "35193653a1ddeee1b1a2a70a313b486f5e0bd50dd9c37e840718604c23495420"
PINNED_PREDECESSOR_GATE_IDENTITY = "7473e04e53539a0d316d21766f48dfcb9d4fdca3a43ec944da02e586e4819d78"
PINNED_PREDECESSOR_MANIFEST_SHA = "555a367bb3c00b80ad6e189ffb723be01bb04531cb596726bd1fbc07719c9ef0"
PINNED_BAT637_UNION_IDENTITY = "e526499dab658992bb528799621833a0cb9dbaf538755ceb4b8b1df37053f069"
PINNED_BAT637_GATE_IDENTITY = "c1d2220943342e02bd55efdac6bf3a4992f5fcd4a00059e94cc21ea56581db4a"
PINNED_BAT636_PAYLOAD_IDENTITY = "d3f07d927c82b538a25695d297596c46624ca4ed178166a451c03dab9b478d5f"
PINNED_BAT632_PAYLOAD_IDENTITY = "736cdd338d3097d02ca6c5a05c434e8b36366caac30db55d574c872b2ca892a1"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1998_2009_structured_row_corpus.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
FORBIDDEN_URLS = frozenset(
    {
        "https://files.12thman.com/history/football/stats/2006-2007/texas.htm",
        "https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm",
    }
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise AuthorityViolation(f"missing child payload file: {path}")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n"
    path.write_text(rendered, encoding="utf-8", newline="\n")


def compute_code_identity(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(b"aggie.structured_row_corpus.code_bundle.v1\n")
    for relative in CODE_BUNDLE_RELATIVE:
        path = repo_root / relative
        if not path.is_file():
            raise AuthorityViolation(f"code bundle member missing: {relative}")
        hasher.update(b"PATH:")
        hasher.update(relative.replace("\\", "/").encode("utf-8"))
        hasher.update(b"\n")
        hasher.update(path.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def _row_identity_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "domain": row.get("domain"),
        "source_url": row.get("source_url"),
        "source_sha256": row.get("source_sha256"),
        "season": row.get("season"),
        "source_row_order": row.get("source_row_order"),
        "source_block": row.get("source_block"),
        "source_table": row.get("source_table"),
        "upstream_payload_identity": row.get("upstream_payload_identity"),
    }


def _row_identity(row: Mapping[str, Any]) -> str:
    return stable_hash(_row_identity_payload(row))


def _convert_row(
    *,
    row: Mapping[str, Any],
    domain: str,
    season: int,
    union_identity: str,
    upstream_jira_key: str,
    upstream_payload_identity: str,
    source_row_order: int,
) -> dict[str, Any]:
    original_text = str(
        row.get("original_text")
        or row.get("event_text")
        or row.get("stat_raw")
        or row.get("team_raw")
        or ""
    )
    converted = {
        "admitted_final_union_membership": True,
        "availability": "NOT_ESTABLISHED",
        "availability_claim": False,
        "classification": "POSTGAME_OFFICIAL_STRUCTURED_EVIDENCE_ONLY",
        "domain": domain,
        "domain_row_order": int(row.get("row_order") or source_row_order),
        "identity_status": "SOURCE_TEXT_ONLY",
        "name_raw": row.get("name_raw"),
        "original_text": original_text,
        "parser_identity": row.get("parser_identity") or "tamu.official.statcrew.preformatted.v1",
        "parser_identity_source": "ROW",
        "player_identity": row.get("player_identity") or "SOURCE_PLAYER_CANDIDATE",
        "quarter_raw": row.get("quarter_raw") or row.get("period_raw"),
        "season": season,
        "source_block": str(row.get("block_index") if row.get("block_index") is not None else ""),
        "source_row_order": int(row.get("source_row_order") or source_row_order),
        "source_sha256": str(row.get("source_sha256") or ""),
        "source_table": domain,
        "source_url": str(row.get("source_url") or ""),
        "stat_group": row.get("stat_group"),
        "stat_raw": row.get("stat_raw"),
        "team_raw": row.get("team_raw"),
        "visitor_raw": row.get("visitor_raw"),
        "home_raw": row.get("home_raw"),
        "union_identity": union_identity,
        "upstream_jira_key": upstream_jira_key,
        "upstream_payload_identity": upstream_payload_identity,
    }
    if not converted["source_url"] or not converted["source_sha256"]:
        raise AuthorityViolation("row missing source URL/SHA provenance")
    converted["row_identity"] = _row_identity(converted)
    return converted


def _rows_from_payload(payload: Mapping[str, Any], season: int, union_identity: str, upstream_jira_key: str, upstream_payload_identity: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {domain: [] for domain in SERIALIZED_DOMAINS}
    rows_groups = list(payload.get("rows") or [])
    for rows in rows_groups:
        for idx, row in enumerate(rows):
            domain = str(row.get("domain") or row.get("source_domain") or "")
            if domain not in out:
                continue
            out[domain].append(
                _convert_row(
                    row=row,
                    domain=domain,
                    season=season,
                    union_identity=union_identity,
                    upstream_jira_key=upstream_jira_key,
                    upstream_payload_identity=upstream_payload_identity,
                    source_row_order=idx,
                )
            )
    return out


def _load_upstream_payload(path: Path, expected_identity: str) -> dict[str, Any]:
    payload = load_json(path)
    if payload.get("payload_identity") != expected_identity:
        raise AuthorityViolation("upstream payload identity drifted")
    return payload


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    predecessor_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_2000_2009_structured_row_corpus_gate.json")
    if predecessor_gate.get("dataset_identity") != PINNED_PREDECESSOR_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-629 predecessor dataset identity rewritten")
    if predecessor_gate.get("gate_identity") != PINNED_PREDECESSOR_GATE_IDENTITY:
        raise AuthorityViolation("BAT-629 predecessor gate identity rewritten")
    predecessor_root = data_root / "features/tamu_official_2000_2009_structured_row_corpus/sha256" / PINNED_PREDECESSOR_DATASET_IDENTITY
    predecessor_manifest = predecessor_root / "corpus_manifest.json"
    if sha256_file(predecessor_manifest) != PINNED_PREDECESSOR_MANIFEST_SHA:
        raise AuthorityViolation("BAT-629 predecessor manifest SHA drifted")
    bat637_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json")
    if bat637_gate.get("gate_identity") != PINNED_BAT637_GATE_IDENTITY:
        raise AuthorityViolation("BAT-637 union gate identity rewritten")
    if bat637_gate.get("union_identity") != PINNED_BAT637_UNION_IDENTITY:
        raise AuthorityViolation("BAT-637 union identity rewritten")
    union_games = list(bat637_gate.get("enriched_official_games") or [])
    admitted_urls = {str(item.get("url") or "") for item in union_games}
    by_season: dict[int, set[str]] = defaultdict(set)
    for game in union_games:
        season = int(game.get("football_season") or game.get("source_season") or 0)
        url = str(game.get("url") or "")
        if url in FORBIDDEN_URLS:
            continue
        by_season[season].add(url)

    child_rows: dict[str, list[dict[str, Any]]] = {}
    for domain in SERIALIZED_DOMAINS:
        filename = CHILD_FILENAMES[domain]
        rows = read_jsonl(predecessor_root / filename)
        filtered = [
            row
            for row in rows
            if str(row.get("source_url") or "") in admitted_urls
            and str(row.get("source_url") or "") not in FORBIDDEN_URLS
        ]
        child_rows[domain] = filtered

    payload_1998 = _load_upstream_payload(
        data_root
        / "features/tamu_official_1998_structured_domains/sha256"
        / PINNED_BAT636_PAYLOAD_IDENTITY
        / "payload.json",
        PINNED_BAT636_PAYLOAD_IDENTITY,
    )
    payload_1999 = _load_upstream_payload(
        data_root
        / "features/tamu_official_1999_structured_domains/sha256"
        / PINNED_BAT632_PAYLOAD_IDENTITY
        / "payload.json",
        PINNED_BAT632_PAYLOAD_IDENTITY,
    )
    add_1998 = _rows_from_payload(payload_1998, 1998, PINNED_BAT637_UNION_IDENTITY, "BAT-636", PINNED_BAT636_PAYLOAD_IDENTITY)
    add_1999 = _rows_from_payload(payload_1999, 1999, PINNED_BAT637_UNION_IDENTITY, "BAT-632", PINNED_BAT632_PAYLOAD_IDENTITY)
    for domain in SERIALIZED_DOMAINS:
        child_rows[domain].extend([row for row in add_1998[domain] if row["source_url"] in by_season[1998]])
        child_rows[domain].extend([row for row in add_1999[domain] if row["source_url"] in by_season[1999]])

    for domain in SERIALIZED_DOMAINS:
        for row in child_rows[domain]:
            if row.get("availability") != "NOT_ESTABLISHED" or row.get("availability_claim"):
                raise AuthorityViolation("participation promoted to availability")
            if str(row.get("source_url") or "") in FORBIDDEN_URLS:
                raise AuthorityViolation("forbidden URL included in child payload")
            if any(token in str(row.get("original_text") or "").lower() for token in ("merged by name", "name-only merge")):
                raise AuthorityViolation("name-only player merge marker detected")

    counts = {
        "seasons": len([s for s in by_season.keys() if 1998 <= s <= 2009]),
        "games": len([u for u in admitted_urls if u]),
        "serialized_rows_total": sum(len(child_rows[d]) for d in SERIALIZED_DOMAINS),
        "ncaa_contest_ids_created": 0,
        "availability_claims": 0,
        "name_only_player_merges": 0,
        "rejected_urls_excluded": len(bat637_gate.get("rejected_official_1998_games") or []),
    }
    coverage_matrix: list[dict[str, Any]] = []
    for season in sorted([s for s in by_season if 1998 <= s <= 2009]):
        for url in sorted(by_season[season]):
            for domain in SERIALIZED_DOMAINS:
                row_count = sum(1 for row in child_rows[domain] if row.get("source_url") == url)
                coverage_matrix.append(
                    {
                        "season": season,
                        "source_url": url,
                        "domain": domain,
                        "serialized_row_count": row_count,
                        "corpus_coverage": "PRESENT" if row_count > 0 else "ABSENT",
                        "union_coverage": "PRESENT" if row_count > 0 else "ABSENT",
                        "warning": None,
                    }
                )
    for domain in SERIALIZED_DOMAINS:
        rows = child_rows[domain]
        counts[f"{domain}_rows"] = len(rows)
        counts[f"{domain}_games_present"] = len({row["source_url"] for row in rows})

    code_identity = compute_code_identity(repo_root)
    child_payloads: dict[str, dict[str, Any]] = {}
    for domain in SERIALIZED_DOMAINS:
        filename = CHILD_FILENAMES[domain]
        child_payloads[domain] = {
            "filename": filename,
            "row_count": len(child_rows[domain]),
            "schema": SCHEMA_VERSION,
        }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "selected_seasons": list(range(1998, 2010)),
        "union_identity": PINNED_BAT637_UNION_IDENTITY,
        "union_gate_identity": PINNED_BAT637_GATE_IDENTITY,
        "predecessor_dataset_identity": PINNED_PREDECESSOR_DATASET_IDENTITY,
        "predecessor_gate_identity": PINNED_PREDECESSOR_GATE_IDENTITY,
        "predecessor_manifest_file_sha256": PINNED_PREDECESSOR_MANIFEST_SHA,
        "code_bundle_relative": list(CODE_BUNDLE_RELATIVE),
        "code_identity": code_identity,
        "validator_code_identity": code_identity,
        "counts": counts,
        "coverage_matrix": coverage_matrix,
        "child_payloads": child_payloads,
        "upstream": {
            "bat632_payload_identity": PINNED_BAT632_PAYLOAD_IDENTITY,
            "bat636_payload_identity": PINNED_BAT636_PAYLOAD_IDENTITY,
        },
    }
    manifest["dataset_identity"] = stable_hash(
        {
            "union_identity": manifest["union_identity"],
            "predecessor_dataset_identity": manifest["predecessor_dataset_identity"],
            "counts": manifest["counts"],
            "coverage_matrix": manifest["coverage_matrix"],
            "child_payloads": manifest["child_payloads"],
            "validator_code_identity": code_identity,
        }
    )
    return {"manifest": manifest, "child_rows": child_rows, "contract": contract}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    manifest = objects["manifest"]
    root = data_root / FEATURE_ROOT / manifest["dataset_identity"]
    child_payloads = {}
    for domain in SERIALIZED_DOMAINS:
        filename = CHILD_FILENAMES[domain]
        path = root / filename
        write_jsonl(path, objects["child_rows"][domain])
        digest = sha256_file(path)
        child_payloads[domain] = {**manifest["child_payloads"][domain], "sha256": digest}
    manifest["child_payloads"] = child_payloads
    write_json(root / "corpus_manifest.json", manifest)
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1998_2009_STRUCTURED_ROW_CORPUS_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "NEW_IMMUTABLE_SUCCESSOR_FROM_BAT629_AND_BAT637",
        "source_id": SOURCE_ID,
        "dataset_identity": manifest["dataset_identity"],
        "union_identity": manifest["union_identity"],
        "union_gate_identity": manifest["union_gate_identity"],
        "predecessor_dataset_identity": PINNED_PREDECESSOR_DATASET_IDENTITY,
        "predecessor_gate_identity": PINNED_PREDECESSOR_GATE_IDENTITY,
        "predecessor_manifest_file_sha256": PINNED_PREDECESSOR_MANIFEST_SHA,
        "selected_seasons": manifest["selected_seasons"],
        "counts": manifest["counts"],
        "child_payloads": manifest["child_payloads"],
        "validator_code_identity": manifest["validator_code_identity"],
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "protected_lane": PROTECTED_LANE,
        "admissions": {
            "bat_523": "IN_PROGRESS",
            "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "retrieval_time_used_as_known_at": False,
            "pit_training_protected_admission": False
        },
        "authority": {
            "ncaa_contest_identity": False,
            "name_only_player_merge": False,
            "participation_as_availability": False,
            "historical_known_at_from_capture_time": False,
        },
    }
    gate["gate_identity"] = compute_identity(gate, "gate_identity")
    write_json(repo_root / GATE_RELATIVE, gate)
    return {
        "dataset_identity": manifest["dataset_identity"],
        "gate_identity": gate["gate_identity"],
        "manifest_path": str(root / "corpus_manifest.json"),
    }


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    if committed.get("predecessor_dataset_identity") != PINNED_PREDECESSOR_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-629 predecessor dataset identity rewritten")
    if committed.get("predecessor_gate_identity") != PINNED_PREDECESSOR_GATE_IDENTITY:
        raise AuthorityViolation("BAT-629 predecessor gate identity rewritten")
    if committed.get("predecessor_manifest_file_sha256") != PINNED_PREDECESSOR_MANIFEST_SHA:
        raise AuthorityViolation("BAT-629 predecessor manifest identity rewritten")
    if committed.get("union_identity") != PINNED_BAT637_UNION_IDENTITY:
        raise AuthorityViolation("BAT-637 union identity rewritten")
    if committed.get("union_gate_identity") != PINNED_BAT637_GATE_IDENTITY:
        raise AuthorityViolation("BAT-637 union gate identity rewritten")
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    expected = materialize(repo_root=repo_root, data_root=data_root)
    recomputed = load_json(repo_root / GATE_RELATIVE)
    if recomputed != committed and gate is not None:
        raise AuthorityViolation("committed gate does not match recomputed materialization")
    return {"result": "PASS", **expected}


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
