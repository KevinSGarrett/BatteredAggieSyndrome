"""2000-2009 official SRC-014 structured row-corpus successor to BAT-620 (BAT-629)."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2002_structured_domains import (
    lake_is_ready as bat617_raw_ready,
    reconstruct_objects as reconstruct_bat617_raw,
    validate_artifact as validate_bat617_raw,
)
from aggie_analytics.data.tamu_official_2003_structured_domains import (
    lake_is_ready as bat611_raw_ready,
    reconstruct_objects as reconstruct_bat611_raw,
    validate_artifact as validate_bat611_raw,
)
from aggie_analytics.data.tamu_official_2004_structured_domains import (
    lake_is_ready as bat606_raw_ready,
    reconstruct_objects as reconstruct_bat606_raw,
    validate_artifact as validate_bat606_raw,
)
from aggie_analytics.data.tamu_official_2005_structured_domains import (
    lake_is_ready as bat601_raw_ready,
    reconstruct_objects as reconstruct_bat601_raw,
    validate_artifact as validate_bat601_raw,
)
from aggie_analytics.data.tamu_official_2006_structured_domains import (
    lake_is_ready as bat596_raw_ready,
    reconstruct_objects as reconstruct_bat596_raw,
    validate_artifact as validate_bat596_raw,
)
from aggie_analytics.data.tamu_official_2000_structured_domains import (
    SCHEMA_VERSION as BAT627_SCHEMA_VERSION,
    SCORING_PARSER_IDENTITY,
    lake_is_ready as bat627_raw_ready,
    reconstruct_objects as reconstruct_bat627_raw,
    validate_artifact as validate_bat627_raw,
)
from aggie_analytics.data.tamu_official_2001_structured_domains import (
    SCHEMA_VERSION as BAT623_SCHEMA_VERSION,
    lake_is_ready as bat623_raw_ready,
    reconstruct_objects as reconstruct_bat623_raw,
    validate_artifact as validate_bat623_raw,
)
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    availability_from_participation,
    parse_scoring_plays,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import (
    SCHEMA_VERSION as BAT591_SCHEMA_VERSION,
    lake_is_ready as bat591_raw_ready,
    parse_preformatted_page,
    reconstruct_objects as reconstruct_bat591_raw,
    validate_artifact as validate_bat591_raw,
)
from aggie_analytics.data.tamu_official_gamebook_union_2000_expanded import (
    FORBIDDEN_UNION_URLS,
    GATE_RELATIVE as BAT628_GATE_RELATIVE,
    OFFICIAL_2000_UNMATCHED_URLS,
    union_manifest_path as bat628_union_manifest_path,
)
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus import (
    ALLOWED_PARSERS as PREDECESSOR_ALLOWED_PARSERS,
    CHILD_FILENAMES,
    FORBIDDEN_URLS as PREDECESSOR_FORBIDDEN_URLS,
    MANIFEST_NAME as PREDECESSOR_MANIFEST_NAME,
    NAME_MERGE_MARKERS,
    PINNED_BAT591_FILE_SHA256,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT596_FILE_SHA256,
    PINNED_BAT596_PAYLOAD_IDENTITY,
    PINNED_BAT601_FILE_SHA256,
    PINNED_BAT601_PAYLOAD_IDENTITY,
    PINNED_BAT606_FILE_SHA256,
    PINNED_BAT606_PAYLOAD_IDENTITY,
    PINNED_BAT611_FILE_SHA256,
    PINNED_BAT611_PAYLOAD_IDENTITY,
    PINNED_BAT617_FILE_SHA256,
    PINNED_BAT617_PAYLOAD_IDENTITY,
    PINNED_BAT618_GATE_IDENTITY as PINNED_BAT619_UNION_GATE_IDENTITY,
    PINNED_BAT618_UNION_IDENTITY as PINNED_BAT619_UNION_IDENTITY,
    PINNED_BAT618_UNION_MANIFEST_FILE_SHA256 as PINNED_BAT619_UNION_MANIFEST_FILE_SHA256,
    PINNED_DATASET_IDENTITY as PINNED_BAT619_DATASET_IDENTITY,
    PINNED_GATE_IDENTITY as PINNED_BAT619_GATE_IDENTITY,
    PINNED_MANIFEST_FILE_SHA256 as PINNED_BAT619_MANIFEST_FILE_SHA256,
    PREFORMATTED_PARSER_IDENTITY,
    REQUIRED_GATE_FIELDS as PREDECESSOR_REQUIRED_GATE_FIELDS,
    SERIALIZED_DOMAINS as PREDECESSOR_SERIALIZED_DOMAINS,
    REQUIRED_ROW_FIELDS,
    _row_identity_payload,
    _season,
    _union_coverage,
    build_coverage_matrix,
    coverage_summary,
    expected_authority,
    expected_scientific_nonclaims,
    index_upstream_rows,
    load_json,
    refuse_name_only_player_merge,
    resolve_parser as predecessor_resolve_parser,
    serialize_jsonl,
    write_json,
)
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus_integrity import (
    FEATURE_ROOT as BAT620_FEATURE_ROOT,
    reconstruct_objects as reconstruct_predecessor_corpus,
)
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_2000_2009_structured_row_corpus.v1"
VALIDATION_CONTRACT_VERSION = (
    "aggie.data.tamu_official_2000_2009_structured_row_corpus.v1"
)
CONTRACT_RELATIVE = (
    "configs/tamu_official_2000_2009_structured_row_corpus_contract.json"
)
GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_2000_2009_structured_row_corpus_gate.json"
)
MODULE_RELATIVE = (
    "src/aggie_analytics/data/tamu_official_2000_2009_structured_row_corpus.py"
)
CONTRACT_ID = "BAT-629-TAMU-OFFICIAL-2000-2009-STRUCTURED-ROW-CORPUS-V1"
DECISION_UNIT = "POST-TASK-SRC014-2000-2009-STRUCTURED-ROW-CORPUS-001"
JIRA_KEY = "BAT-629"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = (
    "TAMU_SRC014_OFFICIAL_2000_2009_STRUCTURED_ROW_CORPUS_CANDIDATE_ONLY"
)
PASS_RESULT = "PASS_OFFICIAL_2000_2009_STRUCTURED_ROW_CORPUS"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
FEATURE_ROOT = "features/tamu_official_2000_2009_structured_row_corpus/sha256"
SERIALIZED_DOMAINS = PREDECESSOR_SERIALIZED_DOMAINS + ("scoring_summary",)
CHILD_DOMAINS = SERIALIZED_DOMAINS
ALLOWED_PARSERS = frozenset(PREDECESSOR_ALLOWED_PARSERS | {SCORING_PARSER_IDENTITY})
SELECTED_SEASONS = (2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009)
FORBIDDEN_URLS = frozenset(
    PREDECESSOR_FORBIDDEN_URLS | OFFICIAL_2000_UNMATCHED_URLS | FORBIDDEN_UNION_URLS
)
GAP_URLS = frozenset(
    {
        "https://files.12thman.com/history/football/stats/2006-2007/texas.htm",
        "https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm",
    }
)
PINNED_BAT628_UNION_IDENTITY = (
    "de887925b47100d9130873cc2878d3931a88f5d5a2ecf2a6b28c22b12a1d9b35"
)
PINNED_BAT628_GATE_IDENTITY = (
    "8d8fcbd413524ce65321212c3c68efe481ddc8e6dda73ab0d6824826dd29e3b2"
)
PINNED_BAT628_UNION_MANIFEST_FILE_SHA256 = (
    "98fa6919315b37726e8aa1cfd373ebcdfe3e9653135c11e72577ea2fafbd5882"
)
PINNED_BAT620_DATASET_IDENTITY = (
    "331817f16df5e5cde22ec730f10faa527be9a641ccb9a95b6ad37c3cf903643d"
)
PINNED_BAT620_GATE_IDENTITY = (
    "c795548724e54d9b28239a6a4810f202a9c1ebdc462450964768bb5e9f0b99b5"
)
PINNED_BAT620_MANIFEST_FILE_SHA256 = (
    "94f09b636bdb06243f79c19eb524a9ff5b5ba454f7da400ea2768a19d44c459f"
)
PINNED_BAT623_PAYLOAD_IDENTITY = (
    "957b631fa7c5d18b3ecd4bcaf48666df6625172f1d1b485255c6204d50cd1aa4"
)
PINNED_BAT623_FILE_SHA256 = (
    "777eb50d68f7284a0c16d97cbb6de42dd450bb098e1836cbf72155bfbda4ffc5"
)
PINNED_BAT627_PAYLOAD_IDENTITY = (
    "3c7499d378ac14658649797219e249051f1501b0c4f774b63dac3314ef60669c"
)
PINNED_BAT627_FILE_SHA256 = (
    "3eec634462ee8a678ca6f58c2e020a12b16e8a3e0ed3e223cbdf0f69694bc935"
)
RAW_BOX_RELATIVE = (
    "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/box_scores"
)
MANIFEST_NAME = "corpus_manifest.json"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
REQUIRED_GATE_FIELDS = PREDECESSOR_REQUIRED_GATE_FIELDS + (
    "predecessor_dataset_identity",
    "predecessor_gate_identity",
    "predecessor_manifest_file_sha256",
    "code_bundle_relative",
)
_RAW_PAYLOAD_CACHE: dict[tuple[str, str], list[dict[str, Any]]] = {}
UPSTREAM_VALIDATORS: tuple[dict[str, Any], ...] = (
    {
        "jira_key": "BAT-591",
        "payload_identity": PINNED_BAT591_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT591_FILE_SHA256,
        "relative_root": "features/tamu_official_statcrew_preformatted/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": BAT591_SCHEMA_VERSION,
        "reconstruct": reconstruct_bat591_raw,
        "validate": validate_bat591_raw,
        "raw_ready": bat591_raw_ready,
    },
    {
        "jira_key": "BAT-596",
        "payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT596_FILE_SHA256,
        "relative_root": "features/tamu_official_2006_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": "aggie.data.tamu_official_2006_structured_domains.v1",
        "reconstruct": reconstruct_bat596_raw,
        "validate": validate_bat596_raw,
        "raw_ready": bat596_raw_ready,
    },
    {
        "jira_key": "BAT-601",
        "payload_identity": PINNED_BAT601_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT601_FILE_SHA256,
        "relative_root": "features/tamu_official_2005_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": "aggie.data.tamu_official_2005_structured_domains.v1",
        "reconstruct": reconstruct_bat601_raw,
        "validate": validate_bat601_raw,
        "raw_ready": bat601_raw_ready,
    },
    {
        "jira_key": "BAT-606",
        "payload_identity": PINNED_BAT606_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT606_FILE_SHA256,
        "relative_root": "features/tamu_official_2004_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": "aggie.data.tamu_official_2004_structured_domains.v1",
        "reconstruct": reconstruct_bat606_raw,
        "validate": validate_bat606_raw,
        "raw_ready": bat606_raw_ready,
    },
    {
        "jira_key": "BAT-611",
        "payload_identity": PINNED_BAT611_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT611_FILE_SHA256,
        "relative_root": "features/tamu_official_2003_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": "aggie.data.tamu_official_2003_structured_domains.v1",
        "reconstruct": reconstruct_bat611_raw,
        "validate": validate_bat611_raw,
        "raw_ready": bat611_raw_ready,
    },
    {
        "jira_key": "BAT-617",
        "payload_identity": PINNED_BAT617_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT617_FILE_SHA256,
        "relative_root": "features/tamu_official_2002_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": "aggie.data.tamu_official_2002_structured_domains.v1",
        "reconstruct": reconstruct_bat617_raw,
        "validate": validate_bat617_raw,
        "raw_ready": bat617_raw_ready,
    },
    {
        "jira_key": "BAT-623",
        "payload_identity": PINNED_BAT623_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT623_FILE_SHA256,
        "relative_root": "features/tamu_official_2001_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": BAT623_SCHEMA_VERSION,
        "reconstruct": reconstruct_bat623_raw,
        "validate": validate_bat623_raw,
        "raw_ready": bat623_raw_ready,
    },
    {
        "jira_key": "BAT-627",
        "payload_identity": PINNED_BAT627_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT627_FILE_SHA256,
        "relative_root": "features/tamu_official_2000_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
        "schema_authorizes_parser_default": True,
        "authorized_schema_version": BAT627_SCHEMA_VERSION,
        "reconstruct": reconstruct_bat627_raw,
        "validate": validate_bat627_raw,
        "raw_ready": bat627_raw_ready,
    },
)


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("row-corpus contract identity drifted")
    return contract


def pinned_code_bundle_identity(repo_root: Path) -> str:
    return str(load_contract(repo_root).get("pinned_code_bundle_identity") or "")


def pinned_dataset_identity(repo_root: Path) -> str:
    return str(load_contract(repo_root).get("pinned_dataset_identity") or "")


def pinned_gate_identity(repo_root: Path) -> str:
    return str(load_contract(repo_root).get("pinned_gate_identity") or "")


def pinned_manifest_file_sha256(repo_root: Path) -> str:
    return str(load_contract(repo_root).get("pinned_manifest_file_sha256") or "")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation(
            "gate is missing required identity fields: " + ", ".join(missing)
        )
    return compute_identity(gate, "gate_identity")


def compute_code_identity(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(b"aggie.integrity.code_bundle.v1\n")
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


def _write_bytes_immutable(payload: bytes, path: Path, *, artifact: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise AuthorityViolation(f"immutable {artifact} collision: {path}")
        return
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def corpus_dir(data_root: Path, dataset_identity: str) -> Path:
    return data_root / FEATURE_ROOT / dataset_identity


def predecessor_root(data_root: Path) -> Path:
    return data_root / BAT620_FEATURE_ROOT / PINNED_BAT620_DATASET_IDENTITY


def payload_path(data_root: Path, source: Mapping[str, Any]) -> Path:
    return (
        data_root
        / source["relative_root"]
        / source["payload_identity"]
        / "payload.json"
    )


def lake_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    del repo_root
    union_path = bat628_union_manifest_path(data_root, PINNED_BAT628_UNION_IDENTITY)
    if not union_path.is_file():
        return False
    pred = predecessor_root(data_root)
    if not (pred / PREDECESSOR_MANIFEST_NAME).is_file():
        return False
    if any(not (pred / CHILD_FILENAMES[domain]).is_file() for domain in CHILD_DOMAINS):
        return False
    if any(
        not payload_path(data_root, source).is_file() for source in UPSTREAM_VALIDATORS
    ):
        return False
    return all(bool(source["raw_ready"](data_root)) for source in UPSTREAM_VALIDATORS)


def upstream_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    return lake_is_ready(data_root, repo_root)


def resolve_parser(
    row: Mapping[str, Any],
    game: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    reconstructed_game: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    parser, parser_source = predecessor_resolve_parser(row, game, source)
    reconstructed = reconstructed_game if reconstructed_game is not None else game
    reconstructed_family = str(
        reconstructed.get("parser_identity") or source["default_parser"]
    ).strip()
    if parser_source == "PAYLOAD_SCHEMA_DEFAULT":
        if not source.get("schema_authorizes_parser_default"):
            raise AuthorityViolation("upstream parser/default change")
        authorized_schema = str(source.get("authorized_schema_version") or "")
        reconstructed_schema = str(reconstructed.get("schema_version") or "")
        if (
            authorized_schema
            and reconstructed_schema
            and reconstructed_schema != authorized_schema
        ):
            raise AuthorityViolation("upstream parser/default change")
        if reconstructed_family != parser:
            raise AuthorityViolation("upstream parser/default change")
    if parser not in ALLOWED_PARSERS:
        raise AuthorityViolation(f"unknown parser: {parser}")
    if reconstructed_family and reconstructed_family not in ALLOWED_PARSERS:
        raise AuthorityViolation("upstream parser/default change")
    return parser, parser_source


def bind_corpus_row(
    raw: Mapping[str, Any],
    *,
    union_game: Mapping[str, Any],
    payload_game: Mapping[str, Any],
    source: Mapping[str, Any],
    payload_identity: str,
    domain_row_order: int,
    reconstructed_game: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    domain = str(raw.get("domain") or "")
    if domain not in SERIALIZED_DOMAINS:
        raise AuthorityViolation(f"unknown domain: {domain}")
    parser, parser_source = resolve_parser(
        raw,
        payload_game,
        source,
        reconstructed_game=reconstructed_game,
    )
    availability = str(raw.get("availability") or "NOT_ESTABLISHED")
    if availability != "NOT_ESTABLISHED":
        raise AuthorityViolation("participation does not establish availability")
    player_identity = str(raw.get("player_identity") or "SOURCE_PLAYER_CANDIDATE")
    if player_identity in NAME_MERGE_MARKERS:
        refuse_name_only_player_merge([raw])
    identity_status = raw.get("identity_status")
    if identity_status in NAME_MERGE_MARKERS:
        refuse_name_only_player_merge([raw])
    source_url = str(raw.get("source_url") or "").strip()
    source_sha256 = str(raw.get("source_sha256") or "").strip()
    if not source_url or not source_sha256:
        raise AuthorityViolation("missing upstream provenance")
    block = raw.get("block_index")
    source_block = "UNKNOWN" if block is None else str(block)
    if "row_order" not in raw:
        raise AuthorityViolation("serialized row is missing source row order")
    row = {
        "admitted_final_union_membership": True,
        "availability": "NOT_ESTABLISHED",
        "availability_claim": False,
        "classification": "POSTGAME_OFFICIAL_STRUCTURED_EVIDENCE_ONLY",
        "domain": domain,
        "domain_row_order": domain_row_order,
        "home_raw": raw.get("home_raw"),
        "identity_status": identity_status
        if identity_status is not None
        else "SOURCE_TEXT_ONLY",
        "name_raw": raw.get("name_raw"),
        "original_text": raw.get("original_text"),
        "parser_identity": parser,
        "parser_identity_source": parser_source,
        "player_identity": player_identity,
        "quarter_raw": raw.get("quarter_raw"),
        "season": _season(union_game),
        "source_block": source_block,
        "source_row_order": raw["row_order"],
        "source_sha256": source_sha256,
        "source_table": str(raw.get("source_domain") or "UNKNOWN"),
        "source_url": source_url,
        "stat_group": raw.get("stat_group"),
        "stat_raw": raw.get("stat_raw"),
        "team_raw": raw.get("team_raw"),
        "union_identity": PINNED_BAT628_UNION_IDENTITY,
        "upstream_jira_key": source["jira_key"],
        "upstream_payload_identity": payload_identity,
        "visitor_raw": raw.get("visitor_raw"),
    }
    if row["source_url"] != union_game["url"]:
        raise AuthorityViolation(f"source URL substitution: {row['source_url']}")
    union_sha = str(union_game.get("source_sha256") or "")
    if union_sha and row["source_sha256"] != union_sha:
        raise AuthorityViolation(f"source SHA substitution: {row['source_url']}")
    row["row_identity"] = stable_hash(_row_identity_payload(row))
    return row


def invoke_upstream_raw_validator(
    source: Mapping[str, Any], *, repo_root: Path, data_root: Path
) -> dict[str, Any]:
    validator: Callable[..., dict[str, Any]] = source["validate"]
    return validator(repo_root=repo_root, data_root=data_root, require_rebuild=True)


def load_raw_validated_upstream_payloads(
    *,
    repo_root: Path,
    data_root: Path,
    stored_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    skip_validators: bool = False,
) -> list[dict[str, Any]]:
    overrides = dict(stored_overrides or {})
    cache_key = (str(repo_root.resolve()), str(data_root.resolve()))
    if not overrides and not skip_validators and cache_key in _RAW_PAYLOAD_CACHE:
        return copy.deepcopy(_RAW_PAYLOAD_CACHE[cache_key])
    loaded: list[dict[str, Any]] = []
    for source in UPSTREAM_VALIDATORS:
        path = payload_path(data_root, source)
        if source["jira_key"] in overrides:
            reconstructed = source["reconstruct"](
                repo_root=repo_root, data_root=data_root
            )
            raw_payload = reconstructed.get("payload")
            if not isinstance(raw_payload, dict):
                raise AuthorityViolation(
                    f"{source['jira_key']} raw reconstruction missing payload"
                )
            stored = dict(overrides[source["jira_key"]])
        else:
            if not skip_validators:
                invoke_upstream_raw_validator(
                    source, repo_root=repo_root, data_root=data_root
                )
            if not path.is_file():
                raise FileNotFoundError(
                    f"missing upstream payload {source['jira_key']}: {path}"
                )
            stored = load_json(path)
            raw_payload = stored
        if stored != raw_payload:
            raise AuthorityViolation("raw capture mismatch")
        file_sha = sha256_file(path) if path.is_file() else str(source["file_sha256"])
        if path.is_file() and file_sha != source["file_sha256"]:
            raise AuthorityViolation(
                f"{source['jira_key']} payload file SHA-256 rewritten"
            )
        recomputed = compute_identity(stored, "payload_identity")
        if (
            recomputed != source["payload_identity"]
            or stored.get("payload_identity") != source["payload_identity"]
        ):
            raise AuthorityViolation(f"{source['jira_key']} payload identity rewritten")
        if recomputed != raw_payload.get("payload_identity"):
            raise AuthorityViolation("coordinated upstream payload identity mutation")
        games = stored.get("games") or []
        rows = stored.get("rows") or []
        if len(games) != len(rows):
            raise AuthorityViolation(f"{source['jira_key']} games/rows length drifted")
        loaded.append(
            {
                "source": source,
                "payload": stored,
                "raw_payload": raw_payload,
                "file_sha256": file_sha,
                "path": str(path),
            }
        )
    if not overrides and not skip_validators:
        _RAW_PAYLOAD_CACHE[cache_key] = copy.deepcopy(loaded)
    return loaded


def require_predecessor_corpus(
    *, repo_root: Path, data_root: Path, predecessor_root_override: Path | None = None
) -> dict[str, Any]:
    union_path = bat628_union_manifest_path(data_root, PINNED_BAT628_UNION_IDENTITY)
    if not union_path.is_file():
        raise FileNotFoundError(f"missing BAT-628 union manifest: {union_path}")
    union_manifest_sha = sha256_file(union_path)
    if union_manifest_sha != PINNED_BAT628_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-628 union manifest file SHA-256 rewritten")
    root = (
        predecessor_root_override
        if predecessor_root_override is not None
        else predecessor_root(data_root)
    )
    manifest_path = root / PREDECESSOR_MANIFEST_NAME
    if not manifest_path.is_file():
        raise AuthorityViolation("missing predecessor manifest")
    stored_manifest = load_json(manifest_path)
    actual_manifest_sha = sha256_file(manifest_path)
    if (
        predecessor_root_override is None
        and actual_manifest_sha != PINNED_BAT620_MANIFEST_FILE_SHA256
    ):
        raise AuthorityViolation("changed predecessor manifest metadata")
    child_shas: dict[str, str] = {}
    for domain in CHILD_DOMAINS:
        child_path = root / CHILD_FILENAMES[domain]
        if not child_path.is_file():
            raise AuthorityViolation(
                f"missing child payload: {CHILD_FILENAMES[domain]}"
            )
        child_shas[domain] = sha256_file(child_path)
        declared = str(
            ((stored_manifest.get("child_payloads") or {}).get(domain) or {}).get(
                "sha256"
            )
            or ""
        )
        if child_shas[domain] != declared:
            raise AuthorityViolation(f"changed child payload: {domain}")
    reconstructed = reconstruct_predecessor_corpus(
        repo_root=repo_root, data_root=data_root
    )
    if reconstructed["manifest"] != stored_manifest:
        raise AuthorityViolation("changed predecessor manifest metadata")
    if reconstructed["gate"].get("gate_identity") != PINNED_BAT620_GATE_IDENTITY:
        raise AuthorityViolation("BAT-620 gate identity rewritten")
    if (
        reconstructed["manifest"].get("dataset_identity")
        != PINNED_BAT620_DATASET_IDENTITY
    ):
        raise AuthorityViolation("BAT-620 dataset identity rewritten")
    return {
        "manifest": stored_manifest,
        "manifest_file_sha256": actual_manifest_sha,
        "child_shas": child_shas,
        "reconstructed": reconstructed,
        "union_manifest_file_sha256": union_manifest_sha,
        "root": root,
    }


def build_corpus_rows(
    union_games: list[Mapping[str, Any]],
    index: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {domain: [] for domain in CHILD_DOMAINS}
    seen_identities: set[str] = set()
    for union_game in union_games:
        url = str(union_game["url"])
        if url not in index:
            raise AuthorityViolation(
                f"admitted union URL has no serialized structured rows: {url}"
            )
        found = index[url]
        domain_orders: Counter[str] = Counter()
        ordered = sorted(
            found["rows"],
            key=lambda row: (
                str(row.get("domain") or ""),
                row.get("block_index") is None,
                row.get("block_index") or 0,
                row.get("row_order"),
            ),
        )
        for raw in ordered:
            domain = str(raw.get("domain") or "")
            bound = bind_corpus_row(
                raw,
                union_game=union_game,
                payload_game=found["game"],
                source=found["source"],
                payload_identity=found["payload_identity"],
                domain_row_order=domain_orders[domain],
                reconstructed_game=found["game"],
            )
            if bound["row_identity"] in seen_identities:
                continue
            seen_identities.add(bound["row_identity"])
            buckets[domain].append(bound)
            domain_orders[domain] += 1
            bound["domain_row_order"] = domain_orders[domain] - 1
    for domain in SERIALIZED_DOMAINS:
        buckets[domain].sort(
            key=lambda row: (
                row["season"],
                row["source_url"],
                row["source_block"],
                row["source_row_order"],
                row["row_identity"],
            )
        )
        for order, row in enumerate(buckets[domain]):
            row["domain_row_order"] = order
            row["row_identity"] = stable_hash(_row_identity_payload(row))
    return buckets


def validate_bound_rows(
    rows: list[Mapping[str, Any]],
    union_urls: set[str],
    union_shas: Mapping[str, str] | None = None,
) -> None:
    seen: set[str] = set()
    previous_order: dict[str, int] = {}
    for row in rows:
        missing = [key for key in REQUIRED_ROW_FIELDS if key not in row]
        if missing:
            raise AuthorityViolation(
                "corpus row missing required fields: " + ", ".join(missing)
            )
        if row.get("admitted_final_union_membership") is not True:
            raise AuthorityViolation(
                "corpus row is not bound to admitted final-union membership"
            )
        url = str(row["source_url"])
        if url in FORBIDDEN_URLS:
            raise AuthorityViolation(f"rejected URL insertion: {url}")
        if url not in union_urls:
            raise AuthorityViolation(f"non-union game insertion: {url}")
        if (
            union_shas is not None
            and url in union_shas
            and str(row.get("source_sha256") or "") != union_shas[url]
        ):
            raise AuthorityViolation(f"source SHA substitution: {url}")
        if row.get("parser_identity") not in ALLOWED_PARSERS:
            raise AuthorityViolation(f"unknown parser: {row.get('parser_identity')}")
        if row.get("domain") not in CHILD_DOMAINS:
            raise AuthorityViolation(f"unknown domain: {row.get('domain')}")
        if row.get("availability") != "NOT_ESTABLISHED" or row.get(
            "availability_claim"
        ):
            availability_from_participation(row)
        if row.get("player_identity") in NAME_MERGE_MARKERS:
            refuse_name_only_player_merge([row])
        expected_identity = stable_hash(_row_identity_payload(row))
        if row.get("row_identity") != expected_identity:
            raise AuthorityViolation("row identity does not recompute")
        if expected_identity in seen:
            raise AuthorityViolation(f"duplicate row: {expected_identity}")
        seen.add(expected_identity)
        key = str(row["domain"])
        order = int(row["domain_row_order"])
        previous = previous_order.get(key)
        if previous is None:
            if order != 0:
                raise AuthorityViolation(f"row-order gap in {key}")
        elif order != previous + 1:
            raise AuthorityViolation(f"row-order gap in {key}")
        previous_order[key] = order
        if int(row["season"]) not in SELECTED_SEASONS:
            raise AuthorityViolation(f"season outside 2000-2009: {row['season']}")
        if (
            not str(row.get("source_url") or "").strip()
            or not str(row.get("source_sha256") or "").strip()
        ):
            raise AuthorityViolation("missing upstream provenance")


def load_union_gate(repo_root: Path) -> dict[str, Any]:
    gate = load_json(repo_root / BAT628_GATE_RELATIVE)
    if gate.get("union_identity") != PINNED_BAT628_UNION_IDENTITY:
        raise AuthorityViolation("BAT-628 union identity rewritten")
    if gate.get("gate_identity") != PINNED_BAT628_GATE_IDENTITY:
        raise AuthorityViolation("BAT-628 gate identity rewritten")
    return gate


def admitted_union_games(union_gate: Mapping[str, Any]) -> list[dict[str, Any]]:
    games = [dict(item) for item in (union_gate.get("enriched_official_games") or [])]
    outside = [item for item in games if _season(item) not in SELECTED_SEASONS]
    if outside:
        raise AuthorityViolation(
            "BAT-628 enriched games include seasons outside 2000-2009"
        )
    forbidden = [item for item in games if str(item.get("url") or "") in FORBIDDEN_URLS]
    if forbidden:
        raise AuthorityViolation(
            "rejected or unmatched URL was admitted to the 2000-2009 corpus"
        )
    games.sort(
        key=lambda item: (
            _season(item),
            str(item.get("calendar_date") or ""),
            str(item.get("url") or ""),
        )
    )
    return games


def raw_box_path(data_root: Path, source_sha256: str) -> Path:
    return data_root / RAW_BOX_RELATIVE / f"sha256_{source_sha256}.html"


def independently_parse_scoring_row(
    raw_play: Mapping[str, Any], union_game: Mapping[str, Any], row_order: int
) -> dict[str, Any]:
    source_url = str(union_game["url"])
    source_sha256 = str(union_game.get("source_sha256") or "")
    if not source_url or not source_sha256:
        raise AuthorityViolation("scoring row missing explicit provenance")
    row = {
        "block_index": None,
        "clock_raw": raw_play.get("clock_raw"),
        "domain": "scoring_summary",
        "event_text": raw_play.get("play_raw"),
        "original_text": raw_play.get("play_raw"),
        "parser_identity": SCORING_PARSER_IDENTITY,
        "period_raw": raw_play.get("quarter_raw"),
        "row_order": row_order,
        "source_domain": "scoring_summary",
        "source_sha256": source_sha256,
        "source_url": source_url,
        "team_raw": raw_play.get("team_raw"),
        "availability": "NOT_ESTABLISHED",
        "player_identity": "SOURCE_PLAYER_CANDIDATE",
    }
    return row


def attach_independent_scoring_rows(
    union_games: list[Mapping[str, Any]],
    index: dict[str, dict[str, Any]],
    data_root: Path,
) -> None:
    for union_game in union_games:
        url = str(union_game["url"])
        found = index.get(url)
        if found is None:
            raise AuthorityViolation(
                f"admitted union URL has no serialized structured rows: {url}"
            )
        existing = [
            row
            for row in found["rows"]
            if str(row.get("domain") or "") == "scoring_summary"
        ]
        if existing:
            continue
        source_sha256 = str(union_game.get("source_sha256") or "")
        raw_path = raw_box_path(data_root, source_sha256)
        if not raw_path.is_file():
            continue
        if sha256_file(raw_path) != source_sha256:
            raise AuthorityViolation(f"raw box SHA-256 rewritten: {url}")
        text = raw_path.read_bytes().decode("latin-1", errors="replace")
        if SCORING_PARSER_IDENTITY and "scoring summary" not in text.lower():
            continue
        plays = parse_scoring_plays(text)
        for row_order, play in enumerate(plays):
            found["rows"].append(
                independently_parse_scoring_row(play, union_game, row_order)
            )


def inspect_gap_pages(
    union_games: list[Mapping[str, Any]],
    buckets: Mapping[str, list[Mapping[str, Any]]],
    data_root: Path,
) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = Counter()
    for domain, rows in buckets.items():
        for row in rows:
            counts[(row["source_url"], domain)] += 1
    inspections: list[dict[str, Any]] = []
    for union_game in union_games:
        url = str(union_game["url"])
        if url not in GAP_URLS:
            continue
        source_sha256 = str(union_game.get("source_sha256") or "")
        raw_path = raw_box_path(data_root, source_sha256)
        if not raw_path.is_file():
            raise AuthorityViolation(f"gap page raw capture missing: {url}")
        body = raw_path.read_bytes()
        if sha256_file(raw_path) != source_sha256:
            raise AuthorityViolation(f"gap page raw SHA-256 rewritten: {url}")
        parsed = parse_preformatted_page(
            body,
            url=url,
            raw_sha256=source_sha256,
            source_season=_season(union_game),
        )
        drive_rows = len(parsed.get("drives") or [])
        pbp_rows = len(parsed.get("play_by_play") or [])
        if drive_rows or pbp_rows:
            raise AuthorityViolation(
                "gap page had reconstructible drive/PBP rows that were left unserialized"
            )
        inspections.append(
            {
                "corpus_drive_rows": int(counts.get((url, "drives"), 0)),
                "corpus_play_by_play_rows": int(counts.get((url, "play_by_play"), 0)),
                "corpus_scoring_rows": int(counts.get((url, "scoring_summary"), 0)),
                "independently_reconstructible_drives": False,
                "independently_reconstructible_play_by_play": False,
                "source_sha256": source_sha256,
                "source_url": url,
                "statcrew_preformatted_drives": drive_rows,
                "statcrew_preformatted_play_by_play": pbp_rows,
                "union_drives": _union_coverage(union_game, "drives"),
                "union_play_by_play": _union_coverage(union_game, "play_by_play"),
            }
        )
    if {item["source_url"] for item in inspections} != set(GAP_URLS):
        raise AuthorityViolation("gap-page inspection set drifted")
    inspections.sort(key=lambda item: item["source_url"])
    return inspections


def reconstruct_objects(
    *,
    repo_root: Path,
    data_root: Path,
    union_gate: Mapping[str, Any] | None = None,
    loaded_payloads: list[dict[str, Any]] | None = None,
    predecessor_root_override: Path | None = None,
    skip_upstream_validators: bool = False,
    stored_overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    contract = load_contract(repo_root)
    code_identity = compute_code_identity(repo_root)
    expected_code = pinned_code_bundle_identity(repo_root)
    if expected_code and code_identity != expected_code:
        raise AuthorityViolation("changed code with stale code identity")
    union = dict(union_gate) if union_gate is not None else load_union_gate(repo_root)
    predecessor = require_predecessor_corpus(
        repo_root=repo_root,
        data_root=data_root,
        predecessor_root_override=predecessor_root_override,
    )
    loaded = (
        loaded_payloads
        if loaded_payloads is not None
        else load_raw_validated_upstream_payloads(
            repo_root=repo_root,
            data_root=data_root,
            stored_overrides=stored_overrides,
            skip_validators=skip_upstream_validators,
        )
    )
    index = index_upstream_rows(loaded)
    games = admitted_union_games(union)
    attach_independent_scoring_rows(games, index, data_root)
    buckets = build_corpus_rows(games, index)
    union_urls = {str(item["url"]) for item in games}
    union_shas = {
        str(item["url"]): str(item.get("source_sha256") or "") for item in games
    }
    for domain in SERIALIZED_DOMAINS:
        validate_bound_rows(buckets[domain], union_urls, union_shas)
    matrix = build_coverage_matrix(games, buckets)
    summary = coverage_summary(matrix)
    child_bytes = {domain: serialize_jsonl(buckets[domain]) for domain in CHILD_DOMAINS}
    child_sha = {
        domain: hashlib.sha256(child_bytes[domain]).hexdigest()
        for domain in CHILD_DOMAINS
    }
    counts = {
        "games": len(games),
        "seasons": len({_season(item) for item in games}),
        "rejected_urls_excluded": len(FORBIDDEN_URLS),
        "oklahoma_2002_excluded": 1,
        "scoring_summary_serialized_rows": len(buckets["scoring_summary"]),
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "availability_claims": 0,
        "serialized_rows_total": sum(
            len(buckets[domain]) for domain in SERIALIZED_DOMAINS
        ),
    }
    for domain in CHILD_DOMAINS:
        counts[f"{domain}_rows"] = len(buckets[domain])
        counts[f"{domain}_games_present"] = summary["by_domain"][domain][
            "corpus_present"
        ]
    expected_games = int(contract.get("expected_games") or 0)
    expected_rows = int(contract.get("expected_serialized_rows") or 0)
    if expected_games and counts["games"] != expected_games:
        raise AuthorityViolation(
            "independent reconstruction proved different membership than the pinned corpus"
        )
    if expected_rows and counts["serialized_rows_total"] != expected_rows:
        raise AuthorityViolation(
            "independent reconstruction proved different rows than the pinned corpus"
        )
    expected_domain_rows = contract.get("expected_domain_rows") or {}
    for domain, expected_count in expected_domain_rows.items():
        if counts[f"{domain}_rows"] != int(expected_count):
            raise AuthorityViolation(
                "independent reconstruction proved different domain rows than the pinned corpus"
            )
    upstream_identities = {
        "bat591_payload_identity": PINNED_BAT591_PAYLOAD_IDENTITY,
        "bat591_payload_file_sha256": PINNED_BAT591_FILE_SHA256,
        "bat596_payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
        "bat596_payload_file_sha256": PINNED_BAT596_FILE_SHA256,
        "bat601_payload_identity": PINNED_BAT601_PAYLOAD_IDENTITY,
        "bat601_payload_file_sha256": PINNED_BAT601_FILE_SHA256,
        "bat606_payload_identity": PINNED_BAT606_PAYLOAD_IDENTITY,
        "bat606_payload_file_sha256": PINNED_BAT606_FILE_SHA256,
        "bat611_payload_identity": PINNED_BAT611_PAYLOAD_IDENTITY,
        "bat611_payload_file_sha256": PINNED_BAT611_FILE_SHA256,
        "bat617_payload_identity": PINNED_BAT617_PAYLOAD_IDENTITY,
        "bat617_payload_file_sha256": PINNED_BAT617_FILE_SHA256,
        "bat618_union_identity": PINNED_BAT619_UNION_IDENTITY,
        "bat618_gate_identity": PINNED_BAT619_UNION_GATE_IDENTITY,
        "bat618_union_manifest_file_sha256": PINNED_BAT619_UNION_MANIFEST_FILE_SHA256,
        "bat619_dataset_identity": PINNED_BAT619_DATASET_IDENTITY,
        "bat619_gate_identity": PINNED_BAT619_GATE_IDENTITY,
        "bat619_manifest_file_sha256": PINNED_BAT619_MANIFEST_FILE_SHA256,
        "bat620_dataset_identity": PINNED_BAT620_DATASET_IDENTITY,
        "bat620_gate_identity": PINNED_BAT620_GATE_IDENTITY,
        "bat620_manifest_file_sha256": PINNED_BAT620_MANIFEST_FILE_SHA256,
        "bat623_payload_identity": PINNED_BAT623_PAYLOAD_IDENTITY,
        "bat623_payload_file_sha256": PINNED_BAT623_FILE_SHA256,
        "bat627_payload_identity": PINNED_BAT627_PAYLOAD_IDENTITY,
        "bat627_payload_file_sha256": PINNED_BAT627_FILE_SHA256,
        "bat628_union_identity": PINNED_BAT628_UNION_IDENTITY,
        "bat628_gate_identity": PINNED_BAT628_GATE_IDENTITY,
        "bat628_union_manifest_file_sha256": PINNED_BAT628_UNION_MANIFEST_FILE_SHA256,
        "validator_code_identity": code_identity,
    }
    child_payloads = {
        domain: {
            "filename": CHILD_FILENAMES[domain],
            "row_count": len(buckets[domain]),
            "schema": SCHEMA_VERSION,
            "sha256": child_sha[domain],
        }
        for domain in CHILD_DOMAINS
    }
    dataset_identity = stable_hash(
        {
            "child_file_sha256": child_sha,
            "counts": counts,
            "coverage_matrix_identity": summary["coverage_matrix_identity"],
            "predecessor_dataset_identity": PINNED_BAT620_DATASET_IDENTITY,
            "schema_version": SCHEMA_VERSION,
            "union_identity": PINNED_BAT628_UNION_IDENTITY,
            "upstream_identities": upstream_identities,
            "validator_code_identity": code_identity,
            "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        }
    )
    expected_dataset = pinned_dataset_identity(repo_root)
    if expected_dataset and dataset_identity != expected_dataset:
        raise AuthorityViolation(
            "dataset identity drifted from the pinned BAT-629 identity"
        )
    scientific = expected_scientific_nonclaims()
    scientific.update(
        {
            "national_completeness": False,
            "production_readiness": False,
            "scoring_summary_serialized_from_union_flags": False,
            "gap_drives_or_pbp_invented": False,
            "all_present_70_70_claim": False,
            "oklahoma_2002_admitted": False,
            "rejected_urls_admitted": False,
            "predecessor_rows_declared_invalid": False,
        }
    )
    authority = expected_authority()
    admissions = {
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_523": "IN_PROGRESS",
        "bat_618_union": "PRESERVED_IMMUTABLE_THROUGH_BAT620_PREDECESSOR",
        "bat_619_corpus": "PRESERVED_IMMUTABLE_THROUGH_BAT620_PREDECESSOR",
        "bat_620_corpus": "PRESERVED_IMMUTABLE_SUPERSEDED_AS_PREDECESSOR",
        "bat_623_domains": "INDEPENDENTLY_RECOMPUTED_EXTERNAL_ROW_PAYLOAD",
        "bat_627_domains": "INDEPENDENTLY_RECOMPUTED_EXTERNAL_ROW_PAYLOAD",
        "bat_628_union": "CONSUMED_AS_2000_EXPANDED_MEMBERSHIP_ONLY",
        "classification": "POSTGAME_OFFICIAL_STRUCTURED_EVIDENCE_ONLY",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "scoring_summary": "SERIALIZED_ONLY_WHEN_INDEPENDENTLY_RECONSTRUCTIBLE",
        "union_admission": "CANDIDATE_ONLY",
    }
    manifest = {
        "child_payloads": child_payloads,
        "code_bundle_relative": list(CODE_BUNDLE_RELATIVE),
        "code_identity": code_identity,
        "counts": counts,
        "coverage_matrix": matrix,
        "coverage_summary": summary,
        "dataset_identity": dataset_identity,
        "parser_identities": sorted(ALLOWED_PARSERS),
        "predecessor_dataset_identity": PINNED_BAT620_DATASET_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT620_GATE_IDENTITY,
        "predecessor_manifest_file_sha256": predecessor["manifest_file_sha256"],
        "schema_version": SCHEMA_VERSION,
        "selected_seasons": list(SELECTED_SEASONS),
        "union_gate_identity": PINNED_BAT628_GATE_IDENTITY,
        "union_identity": PINNED_BAT628_UNION_IDENTITY,
        "upstream": [
            {
                "file_sha256": item["file_sha256"],
                "jira_key": item["source"]["jira_key"],
                "payload_identity": item["source"]["payload_identity"],
                "relative_root": item["source"]["relative_root"],
            }
            for item in loaded
        ],
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": code_identity,
    }
    gate = {
        "admissions": admissions,
        "artifact_type": "TAMU_OFFICIAL_2000_2009_STRUCTURED_ROW_CORPUS_GATE",
        "authority": authority,
        "child_payloads": child_payloads,
        "classification": PASS_CLASSIFICATION,
        "code_bundle_relative": list(CODE_BUNDLE_RELATIVE),
        "contract_id": CONTRACT_ID,
        "coverage_summary": summary,
        "counts": counts,
        "dataset_identity": dataset_identity,
        "decision_unit": DECISION_UNIT,
        "disposition": "NEW_CONTENT_ADDRESSED_2000_2009_ROW_CORPUS_SUCCESSOR",
        "jira_key": JIRA_KEY,
        "gap_inspections": inspect_gap_pages(games, buckets, data_root),
        "predecessor_dataset_identity": PINNED_BAT620_DATASET_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT620_GATE_IDENTITY,
        "predecessor_manifest_file_sha256": predecessor["manifest_file_sha256"],
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": scientific,
        "selected_seasons": list(SELECTED_SEASONS),
        "source_id": SOURCE_ID,
        "union_gate_identity": PINNED_BAT628_GATE_IDENTITY,
        "union_identity": PINNED_BAT628_UNION_IDENTITY,
        "upstream_identities": upstream_identities,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": code_identity,
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    expected_gate = pinned_gate_identity(repo_root)
    if expected_gate and gate["gate_identity"] != expected_gate:
        raise AuthorityViolation(
            "gate identity drifted from the pinned BAT-629 identity"
        )
    return {
        "buckets": buckets,
        "child_bytes": child_bytes,
        "contract": contract,
        "gate": gate,
        "manifest": manifest,
        "predecessor": predecessor,
        "union_games": games,
    }


def materialize_corpus(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    identity = objects["manifest"]["dataset_identity"]
    root = corpus_dir(data_root, identity)
    for domain in CHILD_DOMAINS:
        _write_bytes_immutable(
            objects["child_bytes"][domain],
            root / CHILD_FILENAMES[domain],
            artifact=f"BAT-629 {domain} child",
        )
    manifest_bytes = (
        json.dumps(objects["manifest"], indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _write_bytes_immutable(
        manifest_bytes, root / MANIFEST_NAME, artifact="BAT-629 corpus manifest"
    )
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    validate_artifact(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    return {
        "child_payloads": objects["gate"]["child_payloads"],
        "code_identity": objects["gate"]["validator_code_identity"],
        "counts": objects["gate"]["counts"],
        "dataset_identity": identity,
        "external_root": str(root),
        "gate_identity": objects["gate"]["gate_identity"],
        "manifest_file_sha256": sha256_file(root / MANIFEST_NAME),
    }


def consume_corpus(
    *,
    data_root: Path,
    dataset_identity: str,
    skip_children: Iterable[str] = (),
    corpus_root: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    skipped = tuple(skip_children)
    if skipped:
        raise AuthorityViolation(
            "consumer skips a child payload: " + ", ".join(skipped)
        )
    root = (
        corpus_root
        if corpus_root is not None
        else corpus_dir(data_root, dataset_identity)
    )
    consumed: dict[str, list[dict[str, Any]]] = {}
    for domain in CHILD_DOMAINS:
        path = root / CHILD_FILENAMES[domain]
        if not path.is_file():
            raise AuthorityViolation(f"missing child payload: {path.name}")
        text = path.read_text(encoding="utf-8")
        if not text:
            consumed[domain] = []
            continue
        consumed[domain] = [json.loads(line) for line in text.splitlines() if line]
    return consumed


def _validate_children_against_manifest(
    *,
    children: Mapping[str, list[Mapping[str, Any]]],
    manifest: Mapping[str, Any],
    corpus_root: Path | None = None,
) -> None:
    declared = manifest.get("child_payloads") or {}
    for domain in CHILD_DOMAINS:
        if domain not in children:
            raise AuthorityViolation(f"consumer skips a child payload: {domain}")
        rows = children[domain]
        meta = declared.get(domain) or {}
        if int(meta.get("row_count", -1)) != len(rows):
            raise AuthorityViolation(f"{domain} row count drifted")
        if corpus_root is not None:
            actual_sha = sha256_file(corpus_root / CHILD_FILENAMES[domain])
        else:
            actual_sha = hashlib.sha256(serialize_jsonl(rows)).hexdigest()
        if actual_sha != meta.get("sha256"):
            raise AuthorityViolation(
                f"changed child row with unchanged hash declaration: {domain}"
            )


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
    corpus_root: Path | None = None,
    skip_children: Iterable[str] = (),
    coverage_matrix: list[Mapping[str, Any]] | None = None,
    predecessor_root_override: Path | None = None,
    loaded_payloads: list[dict[str, Any]] | None = None,
    skip_upstream_validators: bool = False,
    stored_overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane")
    if (
        committed.get("result") != PASS_RESULT
        or committed.get("classification") != PASS_CLASSIFICATION
    ):
        raise AuthorityViolation("forged DONE/VERIFIED completion")
    if committed.get("union_identity") != PINNED_BAT628_UNION_IDENTITY:
        raise AuthorityViolation("BAT-628 union identity rewritten")
    if committed.get("union_gate_identity") != PINNED_BAT628_GATE_IDENTITY:
        raise AuthorityViolation("BAT-628 gate identity rewritten")
    if committed.get("predecessor_dataset_identity") != PINNED_BAT620_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-620 dataset identity rewritten")
    expected_code = pinned_code_bundle_identity(repo_root)
    computed_code = compute_code_identity(repo_root)
    if expected_code and committed.get("validator_code_identity") != expected_code:
        raise AuthorityViolation("validator code identity rewritten")
    if expected_code and computed_code != expected_code:
        raise AuthorityViolation("changed code with stale code identity")
    if committed.get("validator_code_identity") != computed_code:
        raise AuthorityViolation("changed code with stale code identity")
    scientific = committed.get("scientific_nonclaims") or {}
    if scientific.get("completeness_claimed") or scientific.get(
        "national_completeness"
    ):
        raise AuthorityViolation("completeness claim inserted")
    if scientific.get("protected_lane_opened"):
        raise AuthorityViolation("protected claim inserted")
    if (committed.get("counts") or {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs created")
    authority = committed.get("authority") or {}
    if authority.get("participation_as_availability") or authority.get(
        "availability_claim"
    ):
        raise AuthorityViolation("participation promoted to availability")
    if authority.get("name_only_player_merge"):
        raise AuthorityViolation("name-only player merge")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not independently recompute")
    dataset_identity = str(committed.get("dataset_identity") or "")
    ready = lake_is_ready(data_root, repo_root)
    if require_rebuild and not ready and corpus_root is None:
        raise AuthorityViolation(
            "external row-corpus reconstruction was required but the data root is not mounted"
        )
    if not ready and corpus_root is None:
        return {
            "dataset_identity": dataset_identity,
            "external_reconstruction": "NOT_MOUNTED",
            "gate": committed,
        }
    root = (
        corpus_root
        if corpus_root is not None
        else corpus_dir(data_root, dataset_identity)
    )
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing corpus manifest: {manifest_path}")
    manifest = load_json(manifest_path)
    if coverage_matrix is not None:
        if coverage_matrix != manifest.get("coverage_matrix"):
            raise AuthorityViolation(
                "changed coverage matrix without corresponding row change"
            )
    children = consume_corpus(
        data_root=data_root,
        dataset_identity=dataset_identity,
        skip_children=skip_children,
        corpus_root=root,
    )
    _validate_children_against_manifest(
        children=children, manifest=manifest, corpus_root=root
    )
    union_games = load_union_gate(repo_root).get("enriched_official_games") or []
    union_urls = {str(item["url"]) for item in union_games}
    union_shas = {
        str(item["url"]): str(item.get("source_sha256") or "") for item in union_games
    }
    for domain in SERIALIZED_DOMAINS:
        validate_bound_rows(children[domain], union_urls, union_shas)
    expected_manifest_sha = pinned_manifest_file_sha256(repo_root)
    if expected_manifest_sha and corpus_root is None:
        actual_manifest_sha = sha256_file(manifest_path)
        if actual_manifest_sha != expected_manifest_sha:
            raise AuthorityViolation("corpus manifest file SHA-256 rewritten")
    if require_rebuild:
        reconstructed = reconstruct_objects(
            repo_root=repo_root,
            data_root=data_root,
            loaded_payloads=loaded_payloads,
            predecessor_root_override=predecessor_root_override,
            skip_upstream_validators=skip_upstream_validators,
            stored_overrides=stored_overrides,
        )
        actual_shas = {
            domain: sha256_file(root / CHILD_FILENAMES[domain])
            for domain in CHILD_DOMAINS
        }
        reconstructed_shas = {
            domain: reconstructed["manifest"]["child_payloads"][domain]["sha256"]
            for domain in CHILD_DOMAINS
        }
        declared_shas = {
            domain: str(
                (manifest.get("child_payloads") or {}).get(domain, {}).get("sha256")
                or ""
            )
            for domain in CHILD_DOMAINS
        }
        children_changed = actual_shas != reconstructed_shas
        declared_matches_actual = declared_shas == actual_shas
        reconstructed_dataset = reconstructed["manifest"]["dataset_identity"]
        if (
            children_changed
            and declared_matches_actual
            and dataset_identity == reconstructed_dataset
        ):
            raise AuthorityViolation(
                "changed row plus recomputed child hash but stale dataset identity"
            )
        if (
            children_changed
            and declared_matches_actual
            and dataset_identity != reconstructed_dataset
        ):
            raise AuthorityViolation("coordinated child and outer rehash")
        if reconstructed["manifest"].get("coverage_matrix") != manifest.get(
            "coverage_matrix"
        ):
            raise AuthorityViolation(
                "changed coverage matrix without corresponding row change"
            )
        if reconstructed["manifest"] != manifest:
            raise AuthorityViolation(
                "committed corpus manifest does not match independent reconstruction"
            )
        if (
            reconstructed["gate"]["gate_identity"] != committed.get("gate_identity")
            or reconstructed["gate"] != committed
        ):
            raise AuthorityViolation(
                "committed gate does not match independent reconstruction"
            )
    return {
        "dataset_identity": dataset_identity,
        "gate": committed,
        "manifest": manifest,
    }
