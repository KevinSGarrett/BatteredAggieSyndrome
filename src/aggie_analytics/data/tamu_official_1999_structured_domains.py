"""Parse source-labeled official 1999 structured domains from BAT-631 captures."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.tamu_official_1999_boxscores import (
    GATE_RELATIVE as BAT631_GATE_RELATIVE,
    lake_is_ready as official_1999_boxscores_are_ready,
    reconstruct_objects as reconstruct_official_1999_boxscores,
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

SCHEMA_VERSION = "aggie.data.tamu_official_1999_structured_domains.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1999_structured_domains_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1999_structured_domains_gate.json"
CONTRACT_ID = "BAT-632-TAMU-OFFICIAL-1999-STRUCTURED-DOMAINS-V1"
DECISION_UNIT = "POST-TASK-SRC014-1999-STRUCTURED-DOMAINS-001"
JIRA_KEY = "BAT-632"
SOURCE_ID = "SRC-014"
SEASON = 1999
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1999_STRUCTURED_DOMAIN_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1999_STRUCTURED_DOMAINS_PARSED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
PINNED_BAT631_GATE_IDENTITY = (
    "f1a236d97f3ecf93fd91d35ecad9a5bf1c54cd591d6e07bd80875329a426aa22"
)
PINNED_BAT631_DATASET_IDENTITY = (
    "36c348e7c5650174798fd241afc0e65e5afdd8868e4033616e04dced31296c8d"
)
PINNED_BAT631_ACQUISITION_IDENTITY = (
    "a4c27c5583f94c1a5de5de17e748569dbd042d33037b8dfa0380fa22e269d86d"
)
PINNED_BAT630_GATE_IDENTITY = (
    "53726e12b28dcb250bac1327a894f623d094a5d365ee60a2f6af965a35defc3a"
)
PINNED_BAT625_GATE_IDENTITY = (
    "38cf419510306d17c203a660051f96da9e186e275833bb763a517cf735b07546"
)
PINNED_BAT621_GATE_IDENTITY = (
    "24b3dd8e800c74885899af1c479cc9c15457eeb6d93b2ab0772825d856f68094"
)
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1999_structured_domains.py"
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
        raise AuthorityViolation(
            "gate is missing required identity fields: " + ", ".join(missing)
        )
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
            raise AuthorityViolation(
                f"PRESENT claimed without serialized {domain} rows"
            )
        if rows and coverage != "PRESENT":
            raise AuthorityViolation(
                f"serialized {domain} rows present without PRESENT coverage"
            )
        for row in rows:
            if not row.get("source_url"):
                raise AuthorityViolation("row URL missing")
            if not row.get("source_sha256"):
                raise AuthorityViolation("row source hash missing")
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


def bind_scoring_summary(
    parsed: dict[str, Any], body: bytes, capture: Mapping[str, Any]
) -> dict[str, Any]:
    text = body.decode("latin-1", errors="replace")
    labeled = SCORING_LABEL_RE.search(text) is not None
    plays = parse_scoring_plays(text) if labeled else []
    rows: list[dict[str, Any]] = []
    for row_order, play in enumerate(plays):
        row = {
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
        if not row["source_url"] or not row["source_sha256"]:
            raise AuthorityViolation("scoring row missing explicit provenance")
        rows.append(row)
    parsed["scoring_summary"] = rows
    if rows:
        parsed["domain_coverage"]["scoring_summary"] = "PRESENT"
    elif labeled:
        parsed["domain_coverage"]["scoring_summary"] = "ABSENT"
        warnings = list(parsed.get("warnings") or [])
        warnings.append("scoring_summary_labeled_but_not_reconstructible")
        parsed["warnings"] = warnings
    else:
        parsed["domain_coverage"]["scoring_summary"] = "ABSENT"
    return parsed


def _bind_rows(game: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in STRUCTURED_DOMAINS:
        for item in game[domain]:
            rows.append({"domain": domain, **item})
    return rows


def _recomputed_row_counts(game: Mapping[str, Any]) -> dict[str, int]:
    return {domain: len(game[domain]) for domain in STRUCTURED_DOMAINS}


def load_1999_captures(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    bat631 = load_json(repo_root / BAT631_GATE_RELATIVE)
    if bat631.get("gate_identity") != PINNED_BAT631_GATE_IDENTITY:
        raise AuthorityViolation("BAT-631 1999 acquisition identity rewritten")
    if bat631.get("dataset_identity") != PINNED_BAT631_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-631 dataset identity rewritten")
    if bat631.get("acquisition_identity") != PINNED_BAT631_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-631 acquisition identity rewritten")
    upstream = bat631.get("upstream_identities") or {}
    if upstream.get("bat630_gate_identity") != PINNED_BAT630_GATE_IDENTITY:
        raise AuthorityViolation("BAT-630 identity rewritten")
    if upstream.get("bat625_gate_identity") != PINNED_BAT625_GATE_IDENTITY:
        raise AuthorityViolation("BAT-625 identity rewritten")
    if upstream.get("bat621_gate_identity") != PINNED_BAT621_GATE_IDENTITY:
        raise AuthorityViolation("BAT-621 identity rewritten")
    if official_1999_boxscores_are_ready(data_root):
        reconstructed = reconstruct_official_1999_boxscores(
            repo_root=repo_root, data_root=data_root
        )
        if reconstructed["gate"] != bat631:
            raise AuthorityViolation(
                "BAT-631 committed gate does not match independent reconstruction"
            )
    captures = list((load_json(data_root / "features/tamu_official_1999_boxscores/capture_index.json").get("captures") or []))
    allowlist = {
        validate_official_url(str(url))
        for url in (load_json(repo_root / "artifacts/data_lake/tamu_official_1999_season_index_gate.json").get("box_score_urls") or [])
    }
    for record in captures:
        url = validate_official_url(str(record.get("url") or ""))
        if url not in allowlist:
            raise AuthorityViolation(f"invented or non-allowlisted capture URL: {url}")
    return captures


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    captures = load_1999_captures(repo_root, data_root)
    games: list[dict[str, Any]] = []
    for capture in captures:
        raw_path = data_root / str(capture["raw_relative_path"])
        if not raw_path.is_file():
            raise AuthorityViolation(
                f"captured raw page missing: {capture['raw_relative_path']}"
            )
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
            "domain_coverage": {
                domain: game["domain_coverage"][domain] for domain in STRUCTURED_DOMAINS
            },
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
            "bat_630_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_631_payload": "CONSUMED_CAPTURES_ONLY",
            "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
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
    if (
        compute_identity(
            {key: value for key, value in payload.items() if key != "payload_identity"},
            "payload_identity",
        )
        != recomputed_identity
    ):
        raise AuthorityViolation("payload identity does not independently recompute")
    counts = {
        "target_games_total": len(captures),
        "parsed_games": len(games),
        "games_1999": len(games),
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
        "artifact_type": "TAMU_OFFICIAL_1999_STRUCTURED_DOMAINS_GATE",
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
            "bat631_gate_identity": PINNED_BAT631_GATE_IDENTITY,
            "bat631_dataset_identity": PINNED_BAT631_DATASET_IDENTITY,
            "bat631_acquisition_identity": PINNED_BAT631_ACQUISITION_IDENTITY,
            "bat630_gate_identity": PINNED_BAT630_GATE_IDENTITY,
            "bat625_gate_identity": PINNED_BAT625_GATE_IDENTITY,
            "bat621_gate_identity": PINNED_BAT621_GATE_IDENTITY,
            "parser_identity": PREFORMATTED_PARSER_IDENTITY,
        },
    }
    if counts["ncaa_contest_ids_created"] or gate["authority"]["ncaa_contest_identity"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(game["availability_claim"] for game in games):
        raise AuthorityViolation("postgame participation treated as availability")
    if payload["availability_claim"] or payload["availability"] != "NOT_ESTABLISHED":
        raise AuthorityViolation("availability promoted")
    gate["gate_identity"] = compute_gate_identity(gate)
    return {
        "contract": contract,
        "gate": gate,
        "payload": payload,
        "captures": captures,
    }


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = (
        data_root
        / objects["contract"]["payloads"]["enriched_root"]
        / payload["payload_identity"]
    )
    write_json(root / "payload.json", payload)
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "payload_identity": payload["payload_identity"],
        "parsed_games": objects["gate"]["counts"]["parsed_games"],
        "serialized_rows_total": objects["gate"]["counts"]["serialized_rows_total"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (data_root / "features/tamu_official_1999_boxscores/capture_index.json").is_file()


def validate_compact_gate(committed: Mapping[str, Any], repo_root: Path) -> None:
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
    for domain in STRUCTURED_DOMAINS:
        if int(counts.get(f"{domain}_present_games") or 0) and not int(
            counts.get(f"{domain}_serialized_rows") or 0
        ):
            raise AuthorityViolation(
                f"PRESENT claimed without serialized {domain} rows"
            )
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat631_gate_identity") != PINNED_BAT631_GATE_IDENTITY:
        raise AuthorityViolation("BAT-631 identity rewritten")
    if upstream.get("bat630_gate_identity") != PINNED_BAT630_GATE_IDENTITY:
        raise AuthorityViolation("BAT-630 identity rewritten")
    if upstream.get("bat625_gate_identity") != PINNED_BAT625_GATE_IDENTITY:
        raise AuthorityViolation("BAT-625 identity rewritten")
    if upstream.get("bat621_gate_identity") != PINNED_BAT621_GATE_IDENTITY:
        raise AuthorityViolation("BAT-621 identity rewritten")
    if upstream.get("parser_identity") != PREFORMATTED_PARSER_IDENTITY:
        raise AuthorityViolation("parser identity mutated")


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
        raise AuthorityViolation(
            "external 1999 structured-domain reconstruction was required but the data root is not mounted"
        )
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation(
            "committed 1999 structured-domain gate does not match independent reconstruction"
        )
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
        raise AuthorityViolation(
            "external structured-domain payload does not match reconstruction"
        )
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
