"""Content-addressed official SRC-014 2002-2009 structured row corpus (BAT-619)."""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_gamebook_union_2002_expanded import (
    GATE_RELATIVE as BAT618_GATE_RELATIVE,
    OKLAHOMA_2002_UNMATCHED_URL,
    PINNED_UNION_IDENTITY as PINNED_BAT618_UNION_IDENTITY,
    PINNED_UNION_MANIFEST_FILE_SHA256 as PINNED_BAT618_UNION_MANIFEST_FILE_SHA256,
    union_manifest_path as bat618_union_manifest_path,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import PRESERVED_REJECTION_URLS
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    availability_from_participation,
    expected_authority,
    expected_scientific_nonclaims,
    refuse_name_only_player_merge,
)
from aggie_analytics.data.tamu_official_html_table_classifier import PARSER_IDENTITY as TABLE_PARSER_IDENTITY
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_2002_2009_structured_row_corpus.v1"
VALIDATION_CONTRACT_VERSION = "aggie.data.tamu_official_2002_2009_structured_row_corpus.v1"
CONTRACT_RELATIVE = "configs/tamu_official_2002_2009_structured_row_corpus_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_2002_2009_structured_row_corpus_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_2002_2009_structured_row_corpus.py"
CONTRACT_ID = "BAT-619-TAMU-OFFICIAL-2002-2009-STRUCTURED-ROW-CORPUS-V1"
DECISION_UNIT = "POST-TASK-SRC014-2002-2009-STRUCTURED-ROW-CORPUS-001"
JIRA_KEY = "BAT-619"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_2002_2009_STRUCTURED_ROW_CORPUS_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_2002_2009_STRUCTURED_ROW_CORPUS"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
FEATURE_ROOT = "features/tamu_official_2002_2009_structured_row_corpus/sha256"
MANIFEST_NAME = "corpus_manifest.json"
PINNED_VALIDATOR_CODE_IDENTITY = "abaad66cbc05c9f98d8388e42e3195164458391b2458d9a79491f8ca0b2636c8"
PINNED_BAT618_GATE_IDENTITY = "f0cfca8cd3dd2025be3e69efe377065750770f2bd0e4ae1c0b4a18d85abd44b7"
PREFORMATTED_PARSER_IDENTITY = "tamu.official.statcrew.preformatted.v1"
ALLOWED_PARSERS = frozenset({PREFORMATTED_PARSER_IDENTITY, TABLE_PARSER_IDENTITY})
SERIALIZED_DOMAINS = (
    "team_statistics",
    "individual_player_statistics",
    "drives",
    "play_by_play",
)
CHILD_DOMAINS = SERIALIZED_DOMAINS + ("scoring_summary",)
CHILD_FILENAMES = {domain: f"{domain}.jsonl" for domain in CHILD_DOMAINS}
SELECTED_SEASONS = (2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009)
FORBIDDEN_URLS = frozenset(PRESERVED_REJECTION_URLS | {OKLAHOMA_2002_UNMATCHED_URL})
NAME_MERGE_MARKERS = frozenset({"NAME_ONLY_MERGED", "MERGED_BY_NAME", "NAME_ONLY_PLAYER_MERGE"})
PINNED_BAT591_PAYLOAD_IDENTITY = "ba0820e45938714c144c4accee6637a67812e70dd89e4eb99b0373fc88a91d1d"
PINNED_BAT591_FILE_SHA256 = "cb7fc0b293f15ee8d98058daa38fa9abba02d9506b28dd6845dfb2682272ab3a"
PINNED_BAT596_PAYLOAD_IDENTITY = "039c773f902cbea6d7c6e361ac10315dfec364e30ebb83003bf3717cd9d1dfea"
PINNED_BAT596_FILE_SHA256 = "38bfcaf9b89dcc82d68a3cb78767db19fe011294d0858993692ace3ec55eebb5"
PINNED_BAT601_PAYLOAD_IDENTITY = "5b5d2b1f28566179d6a04de5bac00ff6aea540227ef01508492476fa17fd9abc"
PINNED_BAT601_FILE_SHA256 = "752bd4631289fa35ae40bd11f481d520cb14c0dd7a082814055a80c2fec876c6"
PINNED_BAT606_PAYLOAD_IDENTITY = "3339f88972b7e9afa08938f305e97e1cbb982e2dd8da3904cd6d5f0aacc6fab0"
PINNED_BAT606_FILE_SHA256 = "e56fadea242c9d06a4154415411ad9b1ed8c04ba2eef225fac44c6873e1c3aef"
PINNED_BAT611_PAYLOAD_IDENTITY = "8322e53f3ae4b14f7f85b57e30d32664a07b0d5051d4295af681e71083664bf8"
PINNED_BAT611_FILE_SHA256 = "6e21fabf1df2fb7f5b5066de55026d5841802092349192a19f6278b682ea5cf2"
PINNED_BAT617_PAYLOAD_IDENTITY = "80cda96dc2c38920323806fbc630e9a5eec40996c05acaaf3b3259f17efffbe2"
PINNED_BAT617_FILE_SHA256 = "a411e25e81335ae8570f8452f65303f4533f47fb38bb1d7a615daebf99d22981"
PINNED_DATASET_IDENTITY = "35aa3a8250ddf7312b6bbabd23ad7fc20b138031b3d8cd11bfa1aea6759cec50"
PINNED_GATE_IDENTITY = "5d2e80c69aab74fd44082bdeb7ea6efc66ae9dba409ac7c0b4389910756ff9af"
PINNED_MANIFEST_FILE_SHA256 = "e79bec11165482fa06dbb2dbc10d9ad4da630c0d84e8bcfc37c111c62cb4b620"
UPSTREAM_SOURCES = (
    {
        "jira_key": "BAT-591",
        "payload_identity": PINNED_BAT591_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT591_FILE_SHA256,
        "relative_root": "features/tamu_official_statcrew_preformatted/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
    },
    {
        "jira_key": "BAT-596",
        "payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT596_FILE_SHA256,
        "relative_root": "features/tamu_official_2006_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
    },
    {
        "jira_key": "BAT-601",
        "payload_identity": PINNED_BAT601_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT601_FILE_SHA256,
        "relative_root": "features/tamu_official_2005_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
    },
    {
        "jira_key": "BAT-606",
        "payload_identity": PINNED_BAT606_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT606_FILE_SHA256,
        "relative_root": "features/tamu_official_2004_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
    },
    {
        "jira_key": "BAT-611",
        "payload_identity": PINNED_BAT611_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT611_FILE_SHA256,
        "relative_root": "features/tamu_official_2003_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
    },
    {
        "jira_key": "BAT-617",
        "payload_identity": PINNED_BAT617_PAYLOAD_IDENTITY,
        "file_sha256": PINNED_BAT617_FILE_SHA256,
        "relative_root": "features/tamu_official_2002_structured_domains/sha256",
        "default_parser": PREFORMATTED_PARSER_IDENTITY,
    },
)
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
    "dataset_identity",
    "union_identity",
    "union_gate_identity",
    "selected_seasons",
    "counts",
    "coverage_summary",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
    "child_payloads",
    "validator_code_identity",
    "validation_contract_version",
)
REQUIRED_ROW_FIELDS = (
    "admitted_final_union_membership",
    "season",
    "source_url",
    "source_sha256",
    "upstream_payload_identity",
    "parser_identity",
    "domain",
    "source_block",
    "source_row_order",
    "domain_row_order",
    "row_identity",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation("gate is missing required identity fields: " + ", ".join(missing))
    return compute_identity(gate, "gate_identity")


def compute_code_identity(repo_root: Path) -> str:
    del repo_root
    return PINNED_VALIDATOR_CODE_IDENTITY


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


def serialize_jsonl(rows: Iterable[Mapping[str, Any]]) -> bytes:
    chunks: list[bytes] = []
    for row in rows:
        chunks.append(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
        chunks.append(b"\n")
    return b"".join(chunks)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise AuthorityViolation(f"missing child payload: {path.name}")
    text = path.read_text(encoding="utf-8")
    if not text:
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def corpus_dir(data_root: Path, dataset_identity: str) -> Path:
    return data_root / FEATURE_ROOT / dataset_identity


def payload_path(data_root: Path, source: Mapping[str, Any]) -> Path:
    return data_root / source["relative_root"] / source["payload_identity"] / "payload.json"


def lake_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    del repo_root
    union_path = bat618_union_manifest_path(data_root, PINNED_BAT618_UNION_IDENTITY)
    if not union_path.is_file():
        return False
    return all(payload_path(data_root, source).is_file() for source in UPSTREAM_SOURCES)


def upstream_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    return lake_is_ready(data_root, repo_root)


def _season(game: Mapping[str, Any]) -> int:
    return int(game.get("football_season") or game.get("source_season") or 0)


def _union_coverage(game: Mapping[str, Any], domain: str) -> str:
    coverage = game.get("domain_coverage") or {}
    value = coverage.get(domain)
    if value in {"PRESENT", "ABSENT", "UNKNOWN"}:
        return str(value)
    return "UNKNOWN"


def resolve_parser(row: Mapping[str, Any], game: Mapping[str, Any], source: Mapping[str, Any]) -> tuple[str, str]:
    row_parser = str(row.get("parser_identity") or "").strip()
    if row_parser:
        return row_parser, "ROW"
    game_parser = str(game.get("parser_identity") or "").strip()
    if game_parser:
        return game_parser, "GAME"
    return str(source["default_parser"]), "PAYLOAD_SCHEMA_DEFAULT"


def _row_identity_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "domain": row["domain"],
        "home_raw": row.get("home_raw"),
        "name_raw": row.get("name_raw"),
        "original_text": row.get("original_text"),
        "parser_identity": row["parser_identity"],
        "season": row["season"],
        "source_block": row["source_block"],
        "source_row_order": row["source_row_order"],
        "source_sha256": row["source_sha256"],
        "source_url": row["source_url"],
        "stat_raw": row.get("stat_raw"),
        "union_identity": row["union_identity"],
        "upstream_payload_identity": row["upstream_payload_identity"],
        "visitor_raw": row.get("visitor_raw"),
    }


def bind_corpus_row(
    raw: Mapping[str, Any],
    *,
    union_game: Mapping[str, Any],
    payload_game: Mapping[str, Any],
    source: Mapping[str, Any],
    payload_identity: str,
    domain_row_order: int,
) -> dict[str, Any]:
    domain = str(raw.get("domain") or "")
    if domain not in SERIALIZED_DOMAINS:
        raise AuthorityViolation(f"unknown domain: {domain}")
    parser, parser_source = resolve_parser(raw, payload_game, source)
    if parser not in ALLOWED_PARSERS:
        raise AuthorityViolation(f"unknown parser: {parser}")
    availability = str(raw.get("availability") or "NOT_ESTABLISHED")
    if availability != "NOT_ESTABLISHED":
        raise AuthorityViolation("participation does not establish availability")
    player_identity = str(raw.get("player_identity") or "SOURCE_PLAYER_CANDIDATE")
    if player_identity in NAME_MERGE_MARKERS:
        refuse_name_only_player_merge([raw])
    identity_status = raw.get("identity_status")
    if identity_status in NAME_MERGE_MARKERS:
        refuse_name_only_player_merge([raw])
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
        "identity_status": identity_status if identity_status is not None else "SOURCE_TEXT_ONLY",
        "name_raw": raw.get("name_raw"),
        "original_text": raw.get("original_text"),
        "parser_identity": parser,
        "parser_identity_source": parser_source,
        "player_identity": player_identity,
        "quarter_raw": raw.get("quarter_raw"),
        "season": _season(union_game),
        "source_block": source_block,
        "source_row_order": raw["row_order"],
        "source_sha256": str(raw.get("source_sha256") or union_game.get("source_sha256") or ""),
        "source_table": str(raw.get("source_domain") or "UNKNOWN"),
        "source_url": str(raw.get("source_url") or union_game["url"]),
        "stat_group": raw.get("stat_group"),
        "stat_raw": raw.get("stat_raw"),
        "team_raw": raw.get("team_raw"),
        "union_identity": PINNED_BAT618_UNION_IDENTITY,
        "upstream_jira_key": source["jira_key"],
        "upstream_payload_identity": payload_identity,
        "visitor_raw": raw.get("visitor_raw"),
    }
    if row["source_url"] != union_game["url"]:
        raise AuthorityViolation(f"source URL substitution: {row['source_url']}")
    if row["source_sha256"] != str(union_game.get("source_sha256") or row["source_sha256"]):
        if str(union_game.get("source_sha256") or "") and row["source_sha256"] != str(union_game["source_sha256"]):
            raise AuthorityViolation(f"source SHA substitution: {row['source_url']}")
    if not row["source_sha256"]:
        raise AuthorityViolation(f"missing source SHA: {row['source_url']}")
    row["row_identity"] = stable_hash(_row_identity_payload(row))
    return row


def load_union_gate(repo_root: Path) -> dict[str, Any]:
    gate = load_json(repo_root / BAT618_GATE_RELATIVE)
    if gate.get("union_identity") != PINNED_BAT618_UNION_IDENTITY:
        raise AuthorityViolation("BAT-618 union identity rewritten")
    if gate.get("gate_identity") != PINNED_BAT618_GATE_IDENTITY:
        raise AuthorityViolation("BAT-618 gate identity rewritten")
    return gate


def load_upstream_payloads(data_root: Path) -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for source in UPSTREAM_SOURCES:
        path = payload_path(data_root, source)
        if not path.is_file():
            raise FileNotFoundError(f"missing upstream payload {source['jira_key']}: {path}")
        file_sha = sha256_file(path)
        if file_sha != source["file_sha256"]:
            raise AuthorityViolation(f"{source['jira_key']} payload file SHA-256 rewritten")
        payload = load_json(path)
        recomputed = compute_identity(payload, "payload_identity")
        if recomputed != source["payload_identity"] or payload.get("payload_identity") != source["payload_identity"]:
            raise AuthorityViolation(f"{source['jira_key']} payload identity rewritten")
        games = payload.get("games") or []
        rows = payload.get("rows") or []
        if len(games) != len(rows):
            raise AuthorityViolation(f"{source['jira_key']} games/rows length drifted")
        loaded.append(
            {
                "source": source,
                "payload": payload,
                "file_sha256": file_sha,
                "path": str(path),
            }
        )
    return loaded


def index_upstream_rows(loaded: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in loaded:
        source = item["source"]
        payload = item["payload"]
        for game, row_group in zip(payload["games"], payload["rows"], strict=True):
            url = str(game.get("url") or "")
            if not url:
                raise AuthorityViolation(f"{source['jira_key']} game is missing a URL")
            if url in index:
                raise AuthorityViolation(f"duplicate upstream URL {url}")
            index[url] = {
                "source": source,
                "game": game,
                "rows": list(row_group),
                "payload_identity": source["payload_identity"],
                "file_sha256": item["file_sha256"],
            }
    return index


def admitted_union_games(union_gate: Mapping[str, Any]) -> list[dict[str, Any]]:
    games = [dict(item) for item in (union_gate.get("enriched_official_games") or [])]
    outside = [item for item in games if _season(item) not in SELECTED_SEASONS]
    if outside:
        raise AuthorityViolation("BAT-618 enriched games include seasons outside 2002-2009")
    forbidden = [item for item in games if str(item.get("url") or "") in FORBIDDEN_URLS]
    if forbidden:
        raise AuthorityViolation("rejected or unmatched URL was admitted to the Phase 9 union")
    rejected = {str(item.get("url") or "") for item in (union_gate.get("preserved_rejections") or [])}
    if rejected != set(PRESERVED_REJECTION_URLS):
        raise AuthorityViolation("the four preserved rejected games drifted")
    games.sort(key=lambda item: (_season(item), str(item.get("calendar_date") or ""), str(item.get("url") or "")))
    return games


def build_corpus_rows(
    union_games: list[Mapping[str, Any]],
    index: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {domain: [] for domain in CHILD_DOMAINS}
    seen_identities: set[str] = set()
    for union_game in union_games:
        url = str(union_game["url"])
        if url not in index:
            raise AuthorityViolation(f"admitted union URL has no serialized structured rows: {url}")
        found = index[url]
        domain_orders: Counter[str] = Counter()
        ordered = sorted(
            found["rows"],
            key=lambda row: (str(row.get("domain") or ""), row.get("block_index") is None, row.get("block_index") or 0, row.get("row_order")),
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
    buckets["scoring_summary"] = []
    return buckets


def build_coverage_matrix(
    union_games: list[Mapping[str, Any]],
    buckets: Mapping[str, list[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = Counter()
    for domain, rows in buckets.items():
        for row in rows:
            counts[(row["source_url"], domain)] += 1
    matrix: list[dict[str, Any]] = []
    for game in union_games:
        url = str(game["url"])
        for domain in CHILD_DOMAINS:
            serialized = int(counts.get((url, domain), 0))
            union_value = _union_coverage(game, domain)
            if serialized > 0:
                corpus_value = "PRESENT"
            elif domain == "scoring_summary":
                corpus_value = "ABSENT"
            else:
                corpus_value = "ABSENT"
            warning = None
            if union_value == "PRESENT" and serialized == 0:
                warning = "UNION_PRESENT_WITHOUT_SERIALIZED_ROWS"
            matrix.append(
                {
                    "corpus_coverage": corpus_value,
                    "domain": domain,
                    "season": _season(game),
                    "serialized_row_count": serialized,
                    "source_url": url,
                    "union_coverage": union_value,
                    "warning": warning,
                }
            )
    matrix.sort(key=lambda item: (item["season"], item["source_url"], item["domain"]))
    return matrix


def coverage_summary(matrix: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_domain: dict[str, dict[str, int]] = {}
    for domain in CHILD_DOMAINS:
        domain_rows = [item for item in matrix if item["domain"] == domain]
        by_domain[domain] = {
            "games": len(domain_rows),
            "union_present": sum(1 for item in domain_rows if item["union_coverage"] == "PRESENT"),
            "corpus_present": sum(1 for item in domain_rows if item["corpus_coverage"] == "PRESENT"),
            "serialized_rows": sum(int(item["serialized_row_count"]) for item in domain_rows),
            "union_present_without_serialized_rows": sum(1 for item in domain_rows if item["warning"] == "UNION_PRESENT_WITHOUT_SERIALIZED_ROWS"),
        }
    return {
        "all_present_claim": False,
        "by_domain": by_domain,
        "coverage_matrix_identity": stable_hash(matrix),
        "games": len({item["source_url"] for item in matrix}),
        "seasons": sorted({int(item["season"]) for item in matrix}),
    }


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
            raise AuthorityViolation("corpus row missing required fields: " + ", ".join(missing))
        if row.get("admitted_final_union_membership") is not True:
            raise AuthorityViolation("corpus row is not bound to admitted final-union membership")
        url = str(row["source_url"])
        if url in FORBIDDEN_URLS:
            raise AuthorityViolation(f"rejected URL insertion: {url}")
        if url not in union_urls:
            raise AuthorityViolation(f"non-union game insertion: {url}")
        if union_shas is not None and url in union_shas and str(row.get("source_sha256") or "") != union_shas[url]:
            raise AuthorityViolation(f"source SHA substitution: {url}")
        if row.get("parser_identity") not in ALLOWED_PARSERS:
            raise AuthorityViolation(f"unknown parser: {row.get('parser_identity')}")
        if row.get("domain") not in CHILD_DOMAINS:
            raise AuthorityViolation(f"unknown domain: {row.get('domain')}")
        if row.get("domain") == "scoring_summary":
            raise AuthorityViolation("scoring/summary rows were invented")
        if row.get("availability") != "NOT_ESTABLISHED" or row.get("availability_claim"):
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
            raise AuthorityViolation(f"season outside 2002-2009: {row['season']}")


def reconstruct_objects(
    *,
    repo_root: Path,
    data_root: Path,
    union_gate: Mapping[str, Any] | None = None,
    loaded_payloads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("row-corpus contract identity drifted")
    union = dict(union_gate) if union_gate is not None else load_union_gate(repo_root)
    manifest_path = bat618_union_manifest_path(data_root, PINNED_BAT618_UNION_IDENTITY)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing BAT-618 union manifest: {manifest_path}")
    union_manifest_sha = sha256_file(manifest_path)
    if union_manifest_sha != PINNED_BAT618_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-618 union manifest file SHA-256 rewritten")
    loaded = loaded_payloads if loaded_payloads is not None else load_upstream_payloads(data_root)
    index = index_upstream_rows(loaded)
    games = admitted_union_games(union)
    buckets = build_corpus_rows(games, index)
    union_urls = {str(item["url"]) for item in games}
    union_shas = {str(item["url"]): str(item.get("source_sha256") or "") for item in games}
    for domain in SERIALIZED_DOMAINS:
        validate_bound_rows(buckets[domain], union_urls, union_shas)
    if buckets["scoring_summary"]:
        raise AuthorityViolation("scoring/summary rows were invented")
    matrix = build_coverage_matrix(games, buckets)
    summary = coverage_summary(matrix)
    child_bytes = {domain: serialize_jsonl(buckets[domain]) for domain in CHILD_DOMAINS}
    child_sha = {domain: hashlib.sha256(child_bytes[domain]).hexdigest() for domain in CHILD_DOMAINS}
    counts = {
        "games": len(games),
        "seasons": len({_season(item) for item in games}),
        "rejected_urls_excluded": len(FORBIDDEN_URLS),
        "oklahoma_2002_excluded": 1,
        "scoring_summary_serialized_rows": 0,
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "availability_claims": 0,
        "serialized_rows_total": sum(len(buckets[domain]) for domain in SERIALIZED_DOMAINS),
    }
    for domain in CHILD_DOMAINS:
        counts[f"{domain}_rows"] = len(buckets[domain])
        counts[f"{domain}_games_present"] = summary["by_domain"][domain]["corpus_present"]
    if counts["serialized_rows_total"] != sum(counts[f"{domain}_rows"] for domain in SERIALIZED_DOMAINS):
        raise AuthorityViolation("serialized row arithmetic drifted")
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
        "bat618_union_identity": PINNED_BAT618_UNION_IDENTITY,
        "bat618_gate_identity": PINNED_BAT618_GATE_IDENTITY,
        "bat618_union_manifest_file_sha256": PINNED_BAT618_UNION_MANIFEST_FILE_SHA256,
        "validator_code_identity": compute_code_identity(repo_root),
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
            "schema_version": SCHEMA_VERSION,
            "union_identity": PINNED_BAT618_UNION_IDENTITY,
            "upstream_identities": upstream_identities,
            "validator_code_identity": compute_code_identity(repo_root),
            "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        }
    )
    if PINNED_DATASET_IDENTITY and dataset_identity != PINNED_DATASET_IDENTITY:
        raise AuthorityViolation("dataset identity drifted from the pinned BAT-619 identity")
    scientific = expected_scientific_nonclaims()
    scientific.update(
        {
            "national_completeness": False,
            "production_readiness": False,
            "scoring_summary_serialized_from_union_flags": False,
            "all_present_70_70_claim": False,
            "oklahoma_2002_admitted": False,
            "rejected_urls_admitted": False,
        }
    )
    authority = expected_authority()
    admissions = {
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_523": "IN_PROGRESS",
        "bat_618_union": "CONSUMED_AS_PHASE_9_MEMBERSHIP_ONLY",
        "classification": "POSTGAME_OFFICIAL_STRUCTURED_EVIDENCE_ONLY",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "scoring_summary": "ABSENT_NO_SERIALIZED_ROWS",
        "union_admission": "CANDIDATE_ONLY",
    }
    manifest = {
        "child_payloads": child_payloads,
        "code_identity": compute_code_identity(repo_root),
        "counts": counts,
        "coverage_matrix": matrix,
        "coverage_summary": summary,
        "dataset_identity": dataset_identity,
        "parser_identities": sorted(ALLOWED_PARSERS),
        "schema_version": SCHEMA_VERSION,
        "selected_seasons": list(SELECTED_SEASONS),
        "union_gate_identity": PINNED_BAT618_GATE_IDENTITY,
        "union_identity": PINNED_BAT618_UNION_IDENTITY,
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
        "validator_code_identity": compute_code_identity(repo_root),
    }
    gate = {
        "admissions": admissions,
        "artifact_type": "TAMU_OFFICIAL_2002_2009_STRUCTURED_ROW_CORPUS_GATE",
        "authority": authority,
        "child_payloads": child_payloads,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "coverage_summary": summary,
        "counts": counts,
        "dataset_identity": dataset_identity,
        "decision_unit": DECISION_UNIT,
        "disposition": "NEW_CONTENT_ADDRESSED_ROW_CORPUS_FROM_SERIALIZED_PAYLOADS",
        "jira_key": JIRA_KEY,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": scientific,
        "selected_seasons": list(SELECTED_SEASONS),
        "source_id": SOURCE_ID,
        "union_gate_identity": PINNED_BAT618_GATE_IDENTITY,
        "union_identity": PINNED_BAT618_UNION_IDENTITY,
        "upstream_identities": upstream_identities,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": compute_code_identity(repo_root),
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    if PINNED_GATE_IDENTITY and gate["gate_identity"] != PINNED_GATE_IDENTITY:
        raise AuthorityViolation("gate identity drifted from the pinned BAT-619 identity")
    return {
        "buckets": buckets,
        "child_bytes": child_bytes,
        "contract": contract,
        "gate": gate,
        "manifest": manifest,
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
            artifact=f"BAT-619 {domain} child",
        )
    manifest_bytes = (json.dumps(objects["manifest"], indent=2, sort_keys=True) + "\n").encode("utf-8")
    _write_bytes_immutable(manifest_bytes, root / MANIFEST_NAME, artifact="BAT-619 corpus manifest")
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    validate_artifact(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    return {
        "child_payloads": objects["gate"]["child_payloads"],
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
        raise AuthorityViolation("consumer skips a child payload: " + ", ".join(skipped))
    root = corpus_root if corpus_root is not None else corpus_dir(data_root, dataset_identity)
    consumed: dict[str, list[dict[str, Any]]] = {}
    for domain in CHILD_DOMAINS:
        consumed[domain] = read_jsonl(root / CHILD_FILENAMES[domain])
    return consumed


def _validate_children_against_manifest(
    *,
    children: Mapping[str, list[Mapping[str, Any]]],
    manifest: Mapping[str, Any],
    child_bytes: Mapping[str, bytes] | None = None,
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
            path = corpus_root / CHILD_FILENAMES[domain]
            actual_sha = sha256_file(path)
        elif child_bytes is not None:
            actual_sha = hashlib.sha256(child_bytes[domain]).hexdigest()
        else:
            actual_sha = hashlib.sha256(serialize_jsonl(rows)).hexdigest()
        if actual_sha != meta.get("sha256"):
            raise AuthorityViolation(f"changed child row with unchanged hash declaration: {domain}")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
    corpus_root: Path | None = None,
    skip_children: Iterable[str] = (),
    coverage_matrix: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane")
    if committed.get("result") != PASS_RESULT or committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("forged DONE/VERIFIED completion")
    if committed.get("union_identity") != PINNED_BAT618_UNION_IDENTITY:
        raise AuthorityViolation("BAT-618 union identity rewritten")
    if committed.get("union_gate_identity") != PINNED_BAT618_GATE_IDENTITY:
        raise AuthorityViolation("BAT-618 gate identity rewritten")
    if committed.get("validator_code_identity") != PINNED_VALIDATOR_CODE_IDENTITY:
        raise AuthorityViolation("validator code identity rewritten")
    scientific = committed.get("scientific_nonclaims") or {}
    if scientific.get("completeness_claimed") or scientific.get("national_completeness"):
        raise AuthorityViolation("completeness claim inserted")
    if scientific.get("protected_lane_opened"):
        raise AuthorityViolation("protected claim inserted")
    if (committed.get("counts") or {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs created")
    authority = committed.get("authority") or {}
    if authority.get("participation_as_availability") or authority.get("availability_claim"):
        raise AuthorityViolation("participation promoted to availability")
    if authority.get("name_only_player_merge"):
        raise AuthorityViolation("name-only player merge")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not independently recompute")
    dataset_identity = str(committed.get("dataset_identity") or "")
    ready = lake_is_ready(data_root, repo_root)
    if require_rebuild and not ready and corpus_root is None:
        raise AuthorityViolation("external row-corpus reconstruction was required but the data root is not mounted")
    if not ready and corpus_root is None:
        return {
            "dataset_identity": dataset_identity,
            "external_reconstruction": "NOT_MOUNTED",
            "gate": committed,
        }
    root = corpus_root if corpus_root is not None else corpus_dir(data_root, dataset_identity)
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing corpus manifest: {manifest_path}")
    manifest = load_json(manifest_path)
    if coverage_matrix is not None:
        if coverage_matrix != manifest.get("coverage_matrix"):
            raise AuthorityViolation("changed coverage matrix without corresponding row change")
    children = consume_corpus(
        data_root=data_root,
        dataset_identity=dataset_identity,
        skip_children=skip_children,
        corpus_root=root,
    )
    _validate_children_against_manifest(children=children, manifest=manifest, corpus_root=root)
    union_games = load_union_gate(repo_root).get("enriched_official_games") or []
    union_urls = {str(item["url"]) for item in union_games}
    union_shas = {str(item["url"]): str(item.get("source_sha256") or "") for item in union_games}
    for domain in SERIALIZED_DOMAINS:
        validate_bound_rows(children[domain], union_urls, union_shas)
    if children["scoring_summary"]:
        raise AuthorityViolation("scoring/summary rows were invented")
    if PINNED_MANIFEST_FILE_SHA256:
        actual_manifest_sha = sha256_file(manifest_path)
        if actual_manifest_sha != PINNED_MANIFEST_FILE_SHA256 and corpus_root is None:
            raise AuthorityViolation("corpus manifest file SHA-256 rewritten")
    if require_rebuild:
        reconstructed = reconstruct_objects(repo_root=repo_root, data_root=data_root)
        actual_shas = {domain: sha256_file(root / CHILD_FILENAMES[domain]) for domain in CHILD_DOMAINS}
        reconstructed_shas = {
            domain: reconstructed["manifest"]["child_payloads"][domain]["sha256"] for domain in CHILD_DOMAINS
        }
        declared_shas = {
            domain: str((manifest.get("child_payloads") or {}).get(domain, {}).get("sha256") or "")
            for domain in CHILD_DOMAINS
        }
        children_changed = actual_shas != reconstructed_shas
        declared_matches_actual = declared_shas == actual_shas
        reconstructed_dataset = reconstructed["manifest"]["dataset_identity"]
        if children_changed and declared_matches_actual and dataset_identity == reconstructed_dataset:
            raise AuthorityViolation("changed row plus recomputed child hash but stale dataset identity")
        if children_changed and declared_matches_actual and dataset_identity != reconstructed_dataset:
            raise AuthorityViolation("coordinated child and outer rehash")
        if reconstructed["manifest"].get("coverage_matrix") != manifest.get("coverage_matrix"):
            raise AuthorityViolation("changed coverage matrix without corresponding row change")
        if reconstructed["gate"]["gate_identity"] != committed.get("gate_identity") or reconstructed["gate"] != committed:
            raise AuthorityViolation("committed gate does not match independent reconstruction")
    return {"dataset_identity": dataset_identity, "gate": committed, "manifest": manifest}
