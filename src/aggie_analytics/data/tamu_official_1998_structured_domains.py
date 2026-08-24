"""Parse source-labeled official 1998 structured domains from BAT-635 captures."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.tamu_official_1998_boxscores import (
    GATE_RELATIVE as BAT635_GATE_RELATIVE,
    lake_is_ready as official_1998_boxscores_are_ready,
    reconstruct_objects as reconstruct_official_1998_boxscores,
)
from aggie_analytics.data.tamu_official_historical_archive import sha256_file, validate_official_url
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    expected_authority,
    expected_scientific_nonclaims,
    parse_scoring_plays,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import (
    DOMAINS as PREFORMATTED_DOMAINS,
    _assign_labeled_blocks,
    extract_pre_blocks,
    parse_preformatted_page,
)
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_1998_structured_domains.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1998_structured_domains_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1998_structured_domains_gate.json"
CONTRACT_ID = "BAT-636-TAMU-OFFICIAL-1998-STRUCTURED-DOMAINS-V1"
DECISION_UNIT = "POST-TASK-SRC014-1998-STRUCTURED-DOMAINS-001"
JIRA_KEY = "BAT-636"
SOURCE_ID = "SRC-014"
SEASON = 1998
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1998_STRUCTURED_DOMAIN_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1998_STRUCTURED_DOMAINS_PARSED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
PINNED_BAT634_GATE_IDENTITY = "f621b849f5692dd6697bd6396086d858966b8d807a6f4ef63d7b0b72d7232306"
PINNED_BAT635_GATE_IDENTITY = "ecc112db8ee339ec80651b7afc021ee5df80751cafdf43ce92d493312cacd260"
PINNED_BAT635_DATASET_IDENTITY = "94d5fe1182a65c35b59f9b2a10d8de1ee561f92a4d6e6e06a53b0a2eded49c15"
PINNED_BAT635_ACQUISITION_IDENTITY = "6dc742a6d359d3800f1474e436734ab523ea17d389e81bca9e9f8c01200f18f7"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1998_structured_domains.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
SCORING_PARSER_IDENTITY = "tamu.official.boxscore.scoring_plays.v1"
SCORING_LABEL_RE = re.compile(r"scoring summary\s*\(final\)", re.IGNORECASE)
STRUCTURED_DOMAINS = PREFORMATTED_DOMAINS + ("scoring_summary",)
PREFORMATTED_PARSER_IDENTITY = "tamu.official.statcrew.preformatted.v1"
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
    "validator_code_identity",
)


def compute_code_identity(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(b"aggie.structured_domains.code_bundle.v1\n")
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation("gate is missing required identity fields: " + ", ".join(missing))
    return compute_identity(gate, "gate_identity")


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
    for domain in PREFORMATTED_DOMAINS:
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
            if row.get("source_url") != parsed["url"] or row.get("source_sha256") != parsed["source_sha256"]:
                raise AuthorityViolation("row provenance drifted")
            if int(row.get("source_season") or 0) != SEASON:
                raise AuthorityViolation("row season substituted")
    parsed["parser_identity"] = PREFORMATTED_PARSER_IDENTITY
    parsed["availability"] = "NOT_ESTABLISHED"
    parsed["availability_claim"] = False
    return parsed


def bind_scoring_summary(parsed: dict[str, Any], body: bytes, capture: Mapping[str, Any]) -> dict[str, Any]:
    text = body.decode("latin-1", errors="replace")
    labeled = SCORING_LABEL_RE.search(text) is not None
    plays = parse_scoring_plays(text) if labeled else []
    rows: list[dict[str, Any]] = []
    for row_order, play in enumerate(plays):
        rows.append(
            {
                "source_url": parsed["url"],
                "source_sha256": parsed["source_sha256"],
                "source_season": SEASON,
                "parent_url": capture.get("parent_url"),
                "source_order": capture.get("source_order"),
                "parser_identity": SCORING_PARSER_IDENTITY,
                "block_index": None,
                "row_order": row_order,
                "source_domain": "scoring_summary",
                "team_raw": play.get("team_raw"),
                "period_raw": play.get("quarter_raw"),
                "clock_raw": play.get("clock_raw"),
                "event_text": play.get("play_raw"),
                "original_text": play.get("play_raw"),
                "availability": "NOT_ESTABLISHED",
                "player_identity": "SOURCE_PLAYER_CANDIDATE",
            }
        )
    parsed["scoring_summary"] = rows
    parsed["domain_coverage"]["scoring_summary"] = "PRESENT" if rows else "ABSENT"
    return parsed


def _bind_rows(game: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in STRUCTURED_DOMAINS:
        for item in game[domain]:
            rows.append({"domain": domain, **item})
    return rows


def _recomputed_row_counts(game: Mapping[str, Any]) -> dict[str, int]:
    return {domain: len(game[domain]) for domain in STRUCTURED_DOMAINS}


def load_1998_captures(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    bat635 = load_json(repo_root / BAT635_GATE_RELATIVE)
    if bat635.get("gate_identity") != PINNED_BAT635_GATE_IDENTITY:
        raise AuthorityViolation("BAT-635 identity rewritten")
    if bat635.get("dataset_identity") != PINNED_BAT635_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-635 dataset identity rewritten")
    if bat635.get("acquisition_identity") != PINNED_BAT635_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-635 acquisition identity rewritten")
    if official_1998_boxscores_are_ready(data_root):
        reconstructed = reconstruct_official_1998_boxscores(repo_root=repo_root, data_root=data_root)
        if reconstructed["gate"] != bat635:
            raise AuthorityViolation("BAT-635 committed gate does not match reconstruction")
    capture_index = load_json(data_root / "features/tamu_official_1998_boxscores/capture_index.json")
    captures = list(capture_index.get("captures") or [])
    allowlist = {
        validate_official_url(str(url))
        for url in (load_json(repo_root / "artifacts/data_lake/tamu_official_1998_season_index_gate.json").get("box_score_urls") or [])
    }
    for record in captures:
        url = validate_official_url(str(record.get("url") or ""))
        if url not in allowlist:
            raise AuthorityViolation(f"invented or non-allowlisted capture URL: {url}")
    return captures


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    captures = load_1998_captures(repo_root, data_root)
    games: list[dict[str, Any]] = []
    for capture in captures:
        raw_path = data_root / str(capture["raw_relative_path"])
        if not raw_path.is_file():
            raise AuthorityViolation(f"captured raw page missing: {capture['raw_relative_path']}")
        if sha256_file(raw_path) != str(capture["raw_sha256"]):
            raise AuthorityViolation("raw capture bytes do not match recorded SHA-256")
        body = raw_path.read_bytes()
        parsed = parse_preformatted_page(
            body,
            url=validate_official_url(str(capture["url"])),
            source_season=SEASON,
            raw_sha256=str(capture["raw_sha256"]),
        )
        parsed = bind_preformatted(parsed, body)
        parsed = bind_scoring_summary(parsed, body, capture)
        parsed["parent_url"] = capture.get("parent_url")
        parsed["source_order"] = capture.get("source_order")
        games.append(parsed)
    coverage_counts = Counter()
    serialized_row_counts = Counter()
    ambiguous_games = 0
    for game in games:
        if game.get("warnings"):
            ambiguous_games += 1
        for domain in STRUCTURED_DOMAINS:
            if game["domain_coverage"][domain] == "PRESENT":
                coverage_counts[domain] += 1
            serialized_row_counts[domain] += len(game[domain])
    compact_games = [
        {
            "url": game["url"],
            "source_sha256": game["source_sha256"],
            "source_season": game["source_season"],
            "parser_identity": game["parser_identity"],
            "domain_coverage": {domain: game["domain_coverage"][domain] for domain in STRUCTURED_DOMAINS},
            "row_counts": _recomputed_row_counts(game),
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
            "bat_635_payload": "CONSUMED_CAPTURES_ONLY",
            "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "ncaa_contest_identity": "NOT_CREATED",
            "name_only_player_merge": "REJECTED",
            "participation_as_availability": "REJECTED",
            "protected_lane": PROTECTED_LANE,
            "union_admission": "NOT_ADMITTED"
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "availability": "NOT_ESTABLISHED",
        "availability_claim": False,
    }
    payload["payload_identity"] = compute_identity(payload, "payload_identity")
    counts = {
        "target_games_total": len(captures),
        "parsed_games": len(games),
        "games_1998": len(games),
        "ambiguous_games": ambiguous_games,
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "availability_claims": 0,
        "games_admitted_to_union": 0,
        "pregame_availability_present": 0,
        "serialized_rows_total": sum(serialized_row_counts.values()),
    }
    for domain in STRUCTURED_DOMAINS:
        counts[f"{domain}_present_games"] = int(coverage_counts[domain])
        counts[f"{domain}_absent_games"] = len(games) - int(coverage_counts[domain])
        counts[f"{domain}_serialized_rows"] = int(serialized_row_counts[domain])
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1998_STRUCTURED_DOMAINS_GATE",
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
        "validator_code_identity": compute_code_identity(repo_root),
        "upstream_identities": {
            "inventory_identity": INVENTORY_IDENTITY,
            "bat634_gate_identity": PINNED_BAT634_GATE_IDENTITY,
            "bat635_gate_identity": PINNED_BAT635_GATE_IDENTITY,
            "bat635_dataset_identity": PINNED_BAT635_DATASET_IDENTITY,
            "bat635_acquisition_identity": PINNED_BAT635_ACQUISITION_IDENTITY,
            "parser_identity": PREFORMATTED_PARSER_IDENTITY,
        },
    }
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
        "serialized_rows_total": objects["gate"]["counts"]["serialized_rows_total"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (data_root / "features/tamu_official_1998_boxscores/capture_index.json").is_file()


def validate_compact_gate(committed: Mapping[str, Any], repo_root: Path) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    if (committed.get("counts") or {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed, repo_root)
    ready = lake_is_ready(data_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external 1998 structured-domain reconstruction required but data root is not mounted")
    if not ready:
        return {"result": "PASS", "gate_identity": committed["gate_identity"], "external_reconstruction": "NOT_MOUNTED"}
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 1998 structured-domain gate does not match reconstruction")
    payload_path = (
        data_root
        / expected["contract"]["payloads"]["enriched_root"]
        / expected["payload"]["payload_identity"]
        / "payload.json"
    )
    if not payload_path.is_file():
        raise AuthorityViolation("external structured-domain payload missing")
    if load_json(payload_path) != expected["payload"]:
        raise AuthorityViolation("external structured-domain payload does not match reconstruction")
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
