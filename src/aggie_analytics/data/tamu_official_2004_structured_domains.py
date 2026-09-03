"""Parse source-labeled official 2004 domains from BAT-605 captures (BAT-606)."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.tamu_official_historical_archive import sha256_file, validate_official_url
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    expected_authority,
    expected_scientific_nonclaims,
)
from aggie_analytics.data.tamu_official_html_table_classifier import PARSER_IDENTITY as TABLE_PARSER_IDENTITY
from aggie_analytics.data.tamu_official_statcrew_preformatted import (
    DOMAINS,
    _assign_labeled_blocks,
    extract_pre_blocks,
    parse_preformatted_page,
)
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_2004_structured_domains.v1"
CONTRACT_RELATIVE = "configs/tamu_official_2004_structured_domains_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_2004_structured_domains_gate.json"
CONTRACT_ID = "BAT-606-TAMU-OFFICIAL-2004-STRUCTURED-DOMAINS-V1"
DECISION_UNIT = "POST-TASK-SRC014-2004-STRUCTURED-DOMAINS-001"
JIRA_KEY = "BAT-606"
SOURCE_ID = "SRC-014"
SEASON = 2004
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_2004_STRUCTURED_DOMAIN_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_2004_STRUCTURED_DOMAINS_PARSED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_2004_boxscores/capture_index.json"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
INVENTORY_GATE_IDENTITY = "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851"
INVENTORY_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
PINNED_BAT605_GATE_IDENTITY = "c570a33661bf194475693f56b2d21baf9a38e67c5ae568f5a531e374356b5c70"
PINNED_BAT605_ACQUISITION_IDENTITY = "7fa30d842696f0e73cc23f53daff1638326d58ce5636b354741eca9cf4c21ad9"
PINNED_BAT605_DATASET_IDENTITY = "6670084e2578fa0e0339668a8b4f47eeaba5c1368d91043203ecfeda38f6c96b"
PINNED_BAT605_GAMES_IDENTITY = "6f7f6505f8e863daeb8d8b7f662fb0ce455a7cb388379815d7d33734cd97ac9b"
PINNED_BAT604_GATE_IDENTITY = "3169f6b14e9f2e78e5af2c3dfa33419d80b37c791968fa39e0ddcf91f3643836"
PINNED_BAT601_GATE_IDENTITY = "a466c5ae9c18cb49a2008c0fc403fe80c9f480b9ba0bb560568651d3cfb393ad"
PINNED_BAT601_PAYLOAD_IDENTITY = "35ccd6ff643dad9248c57d41873f74572c3ac040a642dd0c54197289f87c833d"
PINNED_BAT596_GATE_IDENTITY = "973769e93b22c6e5f30fd8abbaef16bf0abc904e7bc9a5582fc25d4ef06514ba"
PINNED_BAT596_PAYLOAD_IDENTITY = "f4fc2472e90e37adc3d0d4569d8b1225a45acd6ad4d41aa48a9b3dbb39473a9d"
PINNED_BAT591_GATE_IDENTITY = "ed2ce7b95bd046a282116cf50aff84fec1e585f8dee848cc4451bec63bdf668c"
PINNED_BAT591_PAYLOAD_IDENTITY = "c7e061fcafa480f260b8f614ae6481747502ba5d933a786f584da442039fc338"
PREFORMATTED_PARSER_IDENTITY = "tamu.official.statcrew.preformatted.v1"
PINNED_TABLE_PARSER_IDENTITY = "tamu.official.html.table.classifier.v1"
REQUIRED_GATE_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "disposition",
    "source_id",
    "inventory_identity",
    "payload_identity",
    "selected_seasons",
    "counts",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation("gate is missing required identity fields: " + ", ".join(missing))
    return compute_identity(gate, "gate_identity")


def load_2004_captures(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    inventory = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory.get("inventory_identity") != INVENTORY_IDENTITY or inventory.get("gate_identity") != INVENTORY_GATE_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    bat605 = load_json(repo_root / "artifacts/data_lake/tamu_official_2004_boxscore_gate.json")
    if bat605.get("gate_identity") != PINNED_BAT605_GATE_IDENTITY:
        raise AuthorityViolation("BAT-605 2004 acquisition identity rewritten")
    if bat605.get("acquisition_identity") != PINNED_BAT605_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-605 acquisition identity rewritten")
    if bat605.get("dataset_identity") != PINNED_BAT605_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-605 dataset identity rewritten")
    if bat605.get("games_identity") != PINNED_BAT605_GAMES_IDENTITY:
        raise AuthorityViolation("BAT-605 games identity rewritten")
    bat604 = load_json(repo_root / "artifacts/data_lake/tamu_official_2004_season_index_gate.json")
    if bat604.get("gate_identity") != PINNED_BAT604_GATE_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 index identity rewritten")
    bat601 = load_json(repo_root / "artifacts/data_lake/tamu_official_2005_structured_domains_gate.json")
    if bat601.get("gate_identity") != PINNED_BAT601_GATE_IDENTITY:
        raise AuthorityViolation("BAT-601 2005 structured-domain identity rewritten")
    if bat601.get("payload_identity") != PINNED_BAT601_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-601 payload identity rewritten")
    bat596 = load_json(repo_root / "artifacts/data_lake/tamu_official_2006_structured_domains_gate.json")
    if bat596.get("gate_identity") != PINNED_BAT596_GATE_IDENTITY:
        raise AuthorityViolation("BAT-596 2006 structured-domain identity rewritten")
    if bat596.get("payload_identity") != PINNED_BAT596_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-596 payload identity rewritten")
    bat591 = load_json(repo_root / "artifacts/data_lake/tamu_official_statcrew_preformatted_gate.json")
    if bat591.get("gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if bat591.get("payload_identity") != PINNED_BAT591_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-591 payload identity rewritten")
    if TABLE_PARSER_IDENTITY != PINNED_TABLE_PARSER_IDENTITY:
        raise AuthorityViolation("Cycle #13 HTML-table classifier identity mutated")
    allowlist = [validate_official_url(str(url)) for url in (bat604.get("box_score_urls") or [])]
    if len(allowlist) != 12:
        raise AuthorityViolation("BAT-604 allowlist is not the 12 official 2004 box URLs")
    path = data_root / CAPTURE_INDEX_RELATIVE
    if not path.is_file():
        raise AuthorityViolation("BAT-605 capture index missing")
    by_url = {item["url"]: dict(item) for item in (load_json(path).get("captures") or [])}
    captures = []
    for url in allowlist:
        if url not in by_url:
            raise AuthorityViolation(f"BAT-605 capture missing official 2004 URL: {url}")
        record = by_url[url]
        if record.get("url") != url:
            raise AuthorityViolation(f"capture URL substituted: {url}")
        if not record.get("raw_sha256"):
            raise AuthorityViolation(f"capture source SHA missing: {url}")
        if int(record.get("source_season") or 0) != SEASON:
            raise AuthorityViolation(f"capture season drifted: {url}")
        captures.append(record)
    return captures


def bind_preformatted(parsed: dict[str, Any], body: bytes) -> dict[str, Any]:
    blocks = extract_pre_blocks(body.decode("latin-1", errors="replace"))
    assigned = _assign_labeled_blocks(blocks)
    block_index: dict[str, int] = {}
    for domain, domain_blocks in assigned.items():
        if not domain_blocks:
            continue
        try:
            block_index[domain] = blocks.index(domain_blocks[0])
        except ValueError:
            block_index[domain] = 0
    for domain in DOMAINS:
        coverage = parsed["domain_coverage"].get(domain)
        rows = parsed[domain]
        if coverage == "PRESENT" and not rows:
            raise AuthorityViolation(f"PRESENT claimed without serialized {domain} rows")
        if rows and coverage != "PRESENT":
            raise AuthorityViolation(f"serialized {domain} rows present without PRESENT coverage")
        for row in rows:
            row["parser_identity"] = PREFORMATTED_PARSER_IDENTITY
            row["block_index"] = block_index.get(domain)
            row["source_domain"] = domain
            row["availability"] = "NOT_ESTABLISHED"
            row["player_identity"] = "SOURCE_PLAYER_CANDIDATE"
            if row.get("source_url") != parsed["url"]:
                raise AuthorityViolation("row URL substituted")
            if row.get("source_sha256") != parsed["source_sha256"]:
                raise AuthorityViolation("row source hash substituted")
            if int(row.get("source_season") or 0) != SEASON:
                raise AuthorityViolation("row season substituted")
    parsed["parser_identity"] = PREFORMATTED_PARSER_IDENTITY
    parsed["availability"] = "NOT_ESTABLISHED"
    parsed["availability_claim"] = False
    return parsed


def _bind_rows(game: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in DOMAINS:
        for item in game[domain]:
            rows.append({"domain": domain, **item})
    return rows


def _recomputed_row_counts(game: Mapping[str, Any]) -> dict[str, int]:
    return {domain: len(game[domain]) for domain in DOMAINS}


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    captures = load_2004_captures(repo_root, data_root)
    games: list[dict[str, Any]] = []
    for capture in captures:
        raw_path = data_root / capture["raw_relative_path"]
        if not raw_path.is_file():
            raise AuthorityViolation(f"captured raw page missing: {capture['raw_relative_path']}")
        raw_sha256 = str(capture["raw_sha256"])
        if sha256_file(raw_path) != raw_sha256:
            raise AuthorityViolation("raw capture bytes do not match recorded SHA-256")
        body = raw_path.read_bytes()
        parsed = parse_preformatted_page(
            body,
            url=validate_official_url(str(capture["url"])),
            source_season=SEASON,
            raw_sha256=raw_sha256,
        )
        games.append(bind_preformatted(parsed, body))
    coverage_counts = Counter()
    serialized_row_counts = Counter()
    for game in games:
        for domain in DOMAINS:
            if game["domain_coverage"][domain] == "PRESENT":
                coverage_counts[domain] += 1
            serialized_row_counts[domain] += len(game[domain])
    compact_games = [
        {
            "url": game["url"],
            "source_sha256": game["source_sha256"],
            "source_season": game["source_season"],
            "parser_identity": game["parser_identity"],
            "domain_coverage": {domain: game["domain_coverage"][domain] for domain in DOMAINS},
            "row_counts": _recomputed_row_counts(game),
            "rich_structured": game["rich_structured"],
            "warnings": game["warnings"],
        }
        for game in games
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "games": games,
        "rows": [_bind_rows(game) for game in games],
        "admissions": {
            "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
            "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
            "bat_523": "IN_PROGRESS",
            "bat_591_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_596_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_601_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_604_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_605_payload": "CONSUMED_CAPTURES_ONLY",
            "gap_005": "OPEN",
            "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "html_table_classifier": "PINNED_NOT_MUTATED",
            "ncaa_contest_identity": "NOT_CREATED",
            "name_only_player_merge": "REJECTED",
            "participation_as_availability": "REJECTED",
            "protected_lane": PROTECTED_LANE,
            "union_admission": "NOT_ADMITTED",
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "availability": "NOT_ESTABLISHED",
        "availability_claim": False,
    }
    recomputed_identity = compute_identity(payload, "payload_identity")
    payload["payload_identity"] = recomputed_identity
    if compute_identity({key: value for key, value in payload.items() if key != "payload_identity"}, "payload_identity") != recomputed_identity:
        raise AuthorityViolation("payload identity does not independently recompute")
    counts = {
        "target_games_total": 12,
        "parsed_games": len(games),
        "games_2004": len(games),
        "rich_structured_games": sum(1 for game in games if game["rich_structured"]),
        "metadata_only_games": sum(1 for game in games if not game["rich_structured"]),
        "ambiguous_boundary_games": sum(1 for game in games if game["warnings"]),
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "availability_claims": 0,
        "html_tables_classified_pages": 0,
        "html_play_by_play_present_pages": 0,
        "games_admitted_to_union": 0,
        "pregame_availability_present": 0,
        "serialized_rows_total": sum(serialized_row_counts.values()),
    }
    for domain in DOMAINS:
        counts[f"{domain}_present_games"] = int(coverage_counts[domain])
        counts[f"{domain}_absent_games"] = len(games) - int(coverage_counts[domain])
        counts[f"{domain}_serialized_rows"] = int(serialized_row_counts[domain])
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_2004_STRUCTURED_DOMAINS_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "NEW_ENRICHED_PAYLOAD_PRIOR_IDENTITIES_PRESERVED",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "payload_identity": payload["payload_identity"],
        "selected_seasons": [SEASON],
        "counts": counts,
        "games": compact_games,
        "admissions": payload["admissions"],
        "authority": payload["authority"],
        "scientific_nonclaims": payload["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "inventory_identity": INVENTORY_IDENTITY,
            "inventory_gate_identity": INVENTORY_GATE_IDENTITY,
            "bat605_gate_identity": PINNED_BAT605_GATE_IDENTITY,
            "bat605_acquisition_identity": PINNED_BAT605_ACQUISITION_IDENTITY,
            "bat605_dataset_identity": PINNED_BAT605_DATASET_IDENTITY,
            "bat605_games_identity": PINNED_BAT605_GAMES_IDENTITY,
            "bat604_gate_identity": PINNED_BAT604_GATE_IDENTITY,
            "bat601_gate_identity": PINNED_BAT601_GATE_IDENTITY,
            "bat601_payload_identity": PINNED_BAT601_PAYLOAD_IDENTITY,
            "bat596_gate_identity": PINNED_BAT596_GATE_IDENTITY,
            "bat596_payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
            "bat591_gate_identity": PINNED_BAT591_GATE_IDENTITY,
            "bat591_payload_identity": PINNED_BAT591_PAYLOAD_IDENTITY,
            "html_table_classifier_identity": PINNED_TABLE_PARSER_IDENTITY,
        },
    }
    if counts["ncaa_contest_ids_created"] or gate["authority"]["ncaa_contest_identity"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(game["availability_claim"] for game in games):
        raise AuthorityViolation("postgame participation treated as availability")
    if payload["availability_claim"] or payload["availability"] != "NOT_ESTABLISHED":
        raise AuthorityViolation("availability promoted")
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"contract": contract, "gate": gate, "payload": payload, "captures": captures}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = data_root / objects["contract"]["payloads"]["enriched_root"] / payload["payload_identity"]
    write_json(root / "payload.json", payload)
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "payload_identity": payload["payload_identity"],
        "parsed_games": objects["gate"]["counts"]["parsed_games"],
        "rich_structured_games": objects["gate"]["counts"]["rich_structured_games"],
        "serialized_rows_total": objects["gate"]["counts"]["serialized_rows_total"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (data_root / CAPTURE_INDEX_RELATIVE).is_file()


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    authority = committed.get("authority") or {}
    if authority.get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if authority.get("participation_as_availability"):
        raise AuthorityViolation("participation treated as availability")
    if authority.get("name_only_player_merge"):
        raise AuthorityViolation("name-only player merge is forbidden")
    if authority.get("availability_claim"):
        raise AuthorityViolation("availability claimed")
    if authority.get("ncaa_contest_identity"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("result") not in {PASS_RESULT, "PARTIAL_OFFICIAL_2004_STRUCTURED_DOMAINS"}:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("inventory identity rebound incorrectly")
    if committed.get("selected_seasons") != [SEASON]:
        raise AuthorityViolation("selected season tampered")
    if (committed.get("counts") or {}).get("pregame_availability_present"):
        raise AuthorityViolation("pregame availability claimed")
    if (committed.get("counts") or {}).get("availability_claims"):
        raise AuthorityViolation("availability claimed")
    if (committed.get("counts") or {}).get("name_only_player_merges"):
        raise AuthorityViolation("name-only player merge is forbidden")
    counts = committed.get("counts") or {}
    for domain in DOMAINS:
        if int(counts.get(f"{domain}_present_games") or 0) and not int(counts.get(f"{domain}_serialized_rows") or 0):
            raise AuthorityViolation(f"PRESENT claimed without serialized {domain} rows")
    for game in committed.get("games") or []:
        if game.get("parser_identity") != PREFORMATTED_PARSER_IDENTITY:
            raise AuthorityViolation("parser identity changed")
        coverage = game.get("domain_coverage") or {}
        row_counts = game.get("row_counts") or {}
        for domain in DOMAINS:
            if coverage.get(domain) == "PRESENT" and not int(row_counts.get(domain) or 0):
                raise AuthorityViolation(f"PRESENT claimed without serialized {domain} rows")
    if (committed.get("upstream_identities") or {}).get("bat605_gate_identity") != PINNED_BAT605_GATE_IDENTITY:
        raise AuthorityViolation("BAT-605 2004 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat601_gate_identity") != PINNED_BAT601_GATE_IDENTITY:
        raise AuthorityViolation("BAT-601 2005 structured-domain identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat596_gate_identity") != PINNED_BAT596_GATE_IDENTITY:
        raise AuthorityViolation("BAT-596 2006 structured-domain identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat591_gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if (committed.get("upstream_identities") or {}).get("html_table_classifier_identity") != PINNED_TABLE_PARSER_IDENTITY:
        raise AuthorityViolation("Cycle #13 HTML-table classifier identity mutated")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed)
    ready = lake_is_ready(data_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external 2004 structured-domain reconstruction was required but the data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 2004 structured-domain gate does not match independent reconstruction")
    payload_path = (
        data_root
        / expected["contract"]["payloads"]["enriched_root"]
        / expected["payload"]["payload_identity"]
        / "payload.json"
    )
    if not payload_path.is_file():
        raise AuthorityViolation("external structured-domain payload missing")
    stored = load_json(payload_path)
    if stored != expected["payload"]:
        raise AuthorityViolation("external structured-domain payload does not match reconstruction")
    stored_without = {key: value for key, value in stored.items() if key != "payload_identity"}
    if compute_identity(stored_without, "payload_identity") != stored.get("payload_identity"):
        raise AuthorityViolation("external payload rows were altered while payload_identity was left unchanged")
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "payload_identity": expected["payload"]["payload_identity"],
        "parsed_games": expected["gate"]["counts"]["parsed_games"],
        "serialized_rows_total": expected["gate"]["counts"]["serialized_rows_total"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
