"""Parse source-labeled official 2001 domains from BAT-622 captures (BAT-623)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.tamu_official_2001_boxscores import (
    GATE_RELATIVE as BAT622_GATE_RELATIVE,
    lake_is_ready as official_2001_boxscores_are_ready,
    reconstruct_objects as reconstruct_official_2001_boxscores,
)
from aggie_analytics.data.tamu_official_2001_season_index import (
    GATE_RELATIVE as BAT621_GATE_RELATIVE,
    lake_is_ready as official_2001_index_is_ready,
    reconstruct as reconstruct_official_2001_index,
)
from aggie_analytics.data.tamu_official_2002_boxscores import (
    GATE_RELATIVE as BAT615_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_2002_season_index import (
    GATE_RELATIVE as BAT613_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_historical_archive import (
    sha256_file,
    validate_official_url,
)
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    expected_authority,
    expected_scientific_nonclaims,
    parse_scoring_plays,
)
from aggie_analytics.data.tamu_official_html_table_classifier import (
    PARSER_IDENTITY as TABLE_PARSER_IDENTITY,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import (
    DOMAINS as PREFORMATTED_DOMAINS,
    _assign_labeled_blocks,
    extract_pre_blocks,
    parse_preformatted_page,
)
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_2001_structured_domains.v1"
CONTRACT_RELATIVE = "configs/tamu_official_2001_structured_domains_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_2001_structured_domains_gate.json"
CONTRACT_ID = "BAT-623-TAMU-OFFICIAL-2001-STRUCTURED-DOMAINS-V1"
DECISION_UNIT = "POST-TASK-SRC014-2001-STRUCTURED-DOMAINS-001"
JIRA_KEY = "BAT-623"
SOURCE_ID = "SRC-014"
SEASON = 2001
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_2001_STRUCTURED_DOMAIN_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_2001_STRUCTURED_DOMAINS_PARSED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_2001_boxscores/capture_index.json"
BAT617_GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_2002_structured_domains_gate.json"
)
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_2001_structured_domains.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
SCORING_PARSER_IDENTITY = "tamu.official.boxscore.scoring_plays.v1"
SCORING_LABEL_RE = re.compile(r"scoring summary\s*\(final\)", re.IGNORECASE)
STRUCTURED_DOMAINS = PREFORMATTED_DOMAINS + ("scoring_summary",)
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
INVENTORY_GATE_IDENTITY = (
    "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851"
)
INVENTORY_GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
)
PINNED_BAT615_GATE_IDENTITY = (
    "d57e7e50ae9f0d4ee03b83e18df9328f2586da1abac8f3596c00043bb449ad2e"
)
PINNED_BAT615_ACQUISITION_IDENTITY = (
    "c62b407583647b88e884ef59e90c5644cf64a63d077e4d128f7f3405611eb4b3"
)
PINNED_BAT615_DATASET_IDENTITY = (
    "331c64a2855fb6936755e32e71c693985b37da708d526cc980d09192afac5c1a"
)
PINNED_BAT615_GAMES_IDENTITY = (
    "69d969340bfc88fe89e02949f18c9cdd046b066bc702cc3fac6587eb0745cd83"
)
PINNED_BAT613_GATE_IDENTITY = (
    "07cae0a9ce32422706907fa81b9aeb428781c3f76a0ac3c27d9964613793580a"
)
PINNED_BAT613_CAPTURE_IDENTITY = (
    "e9c3d170873a4b1d5cd26fa9e2a4a179d6346444cfba71cfaf40cdf48358222a"
)
PINNED_BAT613_BOX_URL_IDENTITY = (
    "15ed208e59794975b1e28fd0ce9b3c8cda731d5438aedca3fb49328586cd74ac"
)
PINNED_BAT613_PAYLOAD_IDENTITY = (
    "71e518cabe070defa9f5a4551f22d97434a4ff1a9ba13c00159f37cbb3f6d46a"
)
PINNED_BAT613_RAW_SHA256 = (
    "154540d4fc2c8178a44800b6fdb22b5147b3ff0b362111b40fbbd825c9f0933d"
)
PINNED_BAT612_GATE_IDENTITY = (
    "50e92663d6dbfd8c6770746c99c857cc9db2f1761714e5124a8334eff384f99f"
)
PINNED_BAT612_UNION_IDENTITY = (
    "22ab52efad425074ddab75593c882ca7d1fb0fab6e99df160af1681cfc26f5aa"
)
PINNED_BAT611_GATE_IDENTITY = (
    "758ca462a05f9d67ff5017417626eae666902f054037c76207231287cb3f20e9"
)
PINNED_BAT611_PAYLOAD_IDENTITY = (
    "8322e53f3ae4b14f7f85b57e30d32664a07b0d5051d4295af681e71083664bf8"
)
PINNED_BAT610_GATE_IDENTITY = (
    "45329843f7b4683e18c231bbc5c835c7d0e488734d849ea18286d9b098291a13"
)
PINNED_BAT609_GATE_IDENTITY = (
    "1a2b16c74bcfc27ba0afc83611fd817d34aa6a2a71a326fd385721b779d9411e"
)
PINNED_BAT606_GATE_IDENTITY = (
    "bbabb6e97583b33967dd2f883fa8d70082a95fa44eaadb23dbd2a766e33860e6"
)
PINNED_BAT606_PAYLOAD_IDENTITY = (
    "3339f88972b7e9afa08938f305e97e1cbb982e2dd8da3904cd6d5f0aacc6fab0"
)
PINNED_BAT605_GATE_IDENTITY = (
    "c570a33661bf194475693f56b2d21baf9a38e67c5ae568f5a531e374356b5c70"
)
PINNED_BAT604_GATE_IDENTITY = (
    "3169f6b14e9f2e78e5af2c3dfa33419d80b37c791968fa39e0ddcf91f3643836"
)
PINNED_BAT601_GATE_IDENTITY = (
    "b4964041f1b87392ad61c5781c300531051dc9f1a71dfaf630cbeb25af20f96d"
)
PINNED_BAT601_PAYLOAD_IDENTITY = (
    "5b5d2b1f28566179d6a04de5bac00ff6aea540227ef01508492476fa17fd9abc"
)
PINNED_BAT596_GATE_IDENTITY = (
    "57eb2e0b9e449bef0b7935b89c573bfed79110e53d1de414984e0f781baa97a4"
)
PINNED_BAT596_PAYLOAD_IDENTITY = (
    "039c773f902cbea6d7c6e361ac10315dfec364e30ebb83003bf3717cd9d1dfea"
)
PINNED_BAT591_GATE_IDENTITY = (
    "9c3da52dceebd8da0908aa478326196bef2338095a8b5d4c42decaa27df53e16"
)
PINNED_BAT591_PAYLOAD_IDENTITY = (
    "ba0820e45938714c144c4accee6637a67812e70dd89e4eb99b0373fc88a91d1d"
)
PINNED_BAT622_GATE_IDENTITY = (
    "127bea505729cece69c778255c9090486bb31ad66a014d382df134f027fcef8f"
)
PINNED_BAT622_ACQUISITION_IDENTITY = (
    "26865dfd41b05af43883c5f27236cfb7bf62f25fe8f894d6ffde6dd9ad7b55eb"
)
PINNED_BAT622_DATASET_IDENTITY = (
    "289352b9ddee68d2a137542fbb622dffc76340fb33eb0693a794eb60030e194e"
)
PINNED_BAT622_GAMES_IDENTITY = (
    "baeffdc0fe09fa0d90438ceaf797515a02d683a9bc81bada702e7128b274d55b"
)
PINNED_BAT621_GATE_IDENTITY = (
    "24b3dd8e800c74885899af1c479cc9c15457eeb6d93b2ab0772825d856f68094"
)
PINNED_BAT621_CAPTURE_IDENTITY = (
    "aa583efac1716168ac9153c0a56a37df48fa1faf75f9b318c86cd4716a4b7efa"
)
PINNED_BAT621_BOX_URL_IDENTITY = (
    "49c561fd8e27abd0e2f1283013cb748e34f7cafe5ed4d91a25a43e9335b07fc9"
)
PINNED_BAT621_PAYLOAD_IDENTITY = (
    "e04f7d3e3700729d63d805be95e934aa211f9233e2c69d234b95691d63a8ab6a"
)
PINNED_BAT621_RAW_SHA256 = (
    "dc0e00887bf2505ebc4ad0d24c4cac3307f3acd1939584eff9b1d9dc88c5aba1"
)
PINNED_BAT617_GATE_IDENTITY = (
    "d6eca244760bba8963130e070d9ac707cb36af7e715b53e2c3bc60a5bbbed014"
)
PINNED_BAT617_PAYLOAD_IDENTITY = (
    "80cda96dc2c38920323806fbc630e9a5eec40996c05acaaf3b3259f17efffbe2"
)
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
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation(
            "gate is missing required identity fields: " + ", ".join(missing)
        )
    return compute_identity(gate, "gate_identity")


def load_2001_captures(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    inventory = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if (
        inventory.get("inventory_identity") != INVENTORY_IDENTITY
        or inventory.get("gate_identity") != INVENTORY_GATE_IDENTITY
    ):
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    bat622 = load_json(repo_root / BAT622_GATE_RELATIVE)
    if bat622.get("gate_identity") != PINNED_BAT622_GATE_IDENTITY:
        raise AuthorityViolation("BAT-622 2001 acquisition identity rewritten")
    if bat622.get("acquisition_identity") != PINNED_BAT622_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-622 acquisition identity rewritten")
    if bat622.get("dataset_identity") != PINNED_BAT622_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-622 dataset identity rewritten")
    if bat622.get("games_identity") != PINNED_BAT622_GAMES_IDENTITY:
        raise AuthorityViolation("BAT-622 games identity rewritten")
    bat621 = load_json(repo_root / BAT621_GATE_RELATIVE)
    if bat621.get("gate_identity") != PINNED_BAT621_GATE_IDENTITY:
        raise AuthorityViolation("BAT-621 2001 index identity rewritten")
    if bat621.get("payload_identity") != PINNED_BAT621_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-621 payload identity rewritten")
    if bat621.get("capture_identity") != PINNED_BAT621_CAPTURE_IDENTITY:
        raise AuthorityViolation("BAT-621 capture identity rewritten")
    if bat621.get("box_url_identity") != PINNED_BAT621_BOX_URL_IDENTITY:
        raise AuthorityViolation("BAT-621 box-URL identity rewritten")
    if (bat621.get("capture") or {}).get("raw_sha256") != PINNED_BAT621_RAW_SHA256:
        raise AuthorityViolation("BAT-621 season-index raw hash drifted")
    if official_2001_index_is_ready(data_root, repo_root):
        reconstructed_index = reconstruct_official_2001_index(
            repo_root=repo_root, data_root=data_root
        )
        if reconstructed_index["gate"] != bat621:
            raise AuthorityViolation(
                "BAT-621 committed gate does not match independent reconstruction"
            )
        bat621 = reconstructed_index["gate"]
    if official_2001_boxscores_are_ready(data_root):
        reconstructed_box = reconstruct_official_2001_boxscores(
            repo_root=repo_root, data_root=data_root
        )
        if reconstructed_box["gate"] != bat622:
            raise AuthorityViolation(
                "BAT-622 committed gate does not match independent reconstruction"
            )
    bat617 = load_json(repo_root / BAT617_GATE_RELATIVE)
    if bat617.get("gate_identity") != PINNED_BAT617_GATE_IDENTITY:
        raise AuthorityViolation("BAT-617 2002 structured-domain identity rewritten")
    if bat617.get("payload_identity") != PINNED_BAT617_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-617 payload identity rewritten")
    bat615 = load_json(repo_root / BAT615_GATE_RELATIVE)
    if bat615.get("gate_identity") != PINNED_BAT615_GATE_IDENTITY:
        raise AuthorityViolation("BAT-615 2002 acquisition identity rewritten")
    bat613 = load_json(repo_root / BAT613_GATE_RELATIVE)
    if bat613.get("gate_identity") != PINNED_BAT613_GATE_IDENTITY:
        raise AuthorityViolation("BAT-613 2002 index identity rewritten")
    bat612 = load_json(
        repo_root
        / "artifacts/data_lake/tamu_official_gamebook_union_2003_expanded_gate.json"
    )
    if bat612.get("gate_identity") != PINNED_BAT612_GATE_IDENTITY:
        raise AuthorityViolation("BAT-612 2003 union identity rewritten")
    if bat612.get("union_identity") != PINNED_BAT612_UNION_IDENTITY:
        raise AuthorityViolation("BAT-612 union identity rewritten")
    bat611 = load_json(
        repo_root
        / "artifacts/data_lake/tamu_official_2003_structured_domains_gate.json"
    )
    if bat611.get("gate_identity") != PINNED_BAT611_GATE_IDENTITY:
        raise AuthorityViolation("BAT-611 2003 structured-domain identity rewritten")
    if bat611.get("payload_identity") != PINNED_BAT611_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-611 payload identity rewritten")
    bat610 = load_json(
        repo_root / "artifacts/data_lake/tamu_official_2003_boxscore_gate.json"
    )
    if bat610.get("gate_identity") != PINNED_BAT610_GATE_IDENTITY:
        raise AuthorityViolation("BAT-610 2003 acquisition identity rewritten")
    bat609 = load_json(
        repo_root / "artifacts/data_lake/tamu_official_2003_season_index_gate.json"
    )
    if bat609.get("gate_identity") != PINNED_BAT609_GATE_IDENTITY:
        raise AuthorityViolation("BAT-609 2003 index identity rewritten")
    bat606 = load_json(
        repo_root
        / "artifacts/data_lake/tamu_official_2004_structured_domains_gate.json"
    )
    if bat606.get("gate_identity") != PINNED_BAT606_GATE_IDENTITY:
        raise AuthorityViolation("BAT-606 2004 structured-domain identity rewritten")
    if bat606.get("payload_identity") != PINNED_BAT606_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-606 payload identity rewritten")
    bat605 = load_json(
        repo_root / "artifacts/data_lake/tamu_official_2004_boxscore_gate.json"
    )
    if bat605.get("gate_identity") != PINNED_BAT605_GATE_IDENTITY:
        raise AuthorityViolation("BAT-605 2004 acquisition identity rewritten")
    bat604 = load_json(
        repo_root / "artifacts/data_lake/tamu_official_2004_season_index_gate.json"
    )
    if bat604.get("gate_identity") != PINNED_BAT604_GATE_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 index identity rewritten")
    bat601 = load_json(
        repo_root
        / "artifacts/data_lake/tamu_official_2005_structured_domains_gate.json"
    )
    if bat601.get("gate_identity") != PINNED_BAT601_GATE_IDENTITY:
        raise AuthorityViolation("BAT-601 2005 structured-domain identity rewritten")
    if bat601.get("payload_identity") != PINNED_BAT601_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-601 payload identity rewritten")
    bat596 = load_json(
        repo_root
        / "artifacts/data_lake/tamu_official_2006_structured_domains_gate.json"
    )
    if bat596.get("gate_identity") != PINNED_BAT596_GATE_IDENTITY:
        raise AuthorityViolation("BAT-596 2006 structured-domain identity rewritten")
    if bat596.get("payload_identity") != PINNED_BAT596_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-596 payload identity rewritten")
    bat591 = load_json(
        repo_root / "artifacts/data_lake/tamu_official_statcrew_preformatted_gate.json"
    )
    if bat591.get("gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if bat591.get("payload_identity") != PINNED_BAT591_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-591 payload identity rewritten")
    if TABLE_PARSER_IDENTITY != PINNED_TABLE_PARSER_IDENTITY:
        raise AuthorityViolation("Cycle #13 HTML-table classifier identity mutated")
    allowlist = [
        validate_official_url(str(url)) for url in (bat621.get("box_score_urls") or [])
    ]
    if not allowlist:
        raise AuthorityViolation(
            "BAT-621 reconstruction emitted no official 2001 box URLs"
        )
    path = data_root / CAPTURE_INDEX_RELATIVE
    if not path.is_file():
        raise AuthorityViolation("BAT-622 capture index missing")
    by_url = {
        item["url"]: dict(item) for item in (load_json(path).get("captures") or [])
    }
    extra = sorted(set(by_url) - set(allowlist))
    if extra:
        raise AuthorityViolation(f"invented or non-allowlisted capture URL: {extra}")
    captures = []
    for source_order, url in enumerate(allowlist, start=1):
        if url not in by_url:
            raise AuthorityViolation(
                f"BAT-622 capture missing official 2001 URL: {url}"
            )
        record = by_url[url]
        if record.get("url") != url:
            raise AuthorityViolation(f"capture URL substituted: {url}")
        if not record.get("raw_sha256"):
            raise AuthorityViolation(f"capture source SHA missing: {url}")
        if not record.get("source_url") and not record.get("url"):
            raise AuthorityViolation(f"capture URL missing: {url}")
        if not record.get("response_sha256"):
            raise AuthorityViolation(f"response SHA missing for {url}")
        if record.get("response_sha256") != record.get("raw_sha256"):
            raise AuthorityViolation(
                f"response SHA and stored file SHA disagree: {url}"
            )
        if int(record.get("source_season") or 0) != SEASON:
            raise AuthorityViolation(f"capture season drifted: {url}")
        if int(record.get("source_order") or 0) != source_order:
            raise AuthorityViolation(f"source order drifted for {url}")
        if not record.get("parent_url"):
            raise AuthorityViolation(f"parent_url missing for {url}")
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
            "upstream_identity": PINNED_BAT622_GATE_IDENTITY,
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


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    captures = load_2001_captures(repo_root, data_root)
    games: list[dict[str, Any]] = []
    for capture in captures:
        raw_path = data_root / capture["raw_relative_path"]
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
    for game in games:
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
            "bat_605_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_606_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_609_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_610_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_611_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_612_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_613_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_615_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_617_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_621_payload": "CONSUMED_INDEX_CAPTURE_ONLY",
            "bat_622_payload": "CONSUMED_CAPTURES_ONLY",
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
        "games_2001": len(games),
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
    for domain in STRUCTURED_DOMAINS:
        counts[f"{domain}_present_games"] = int(coverage_counts[domain])
        counts[f"{domain}_absent_games"] = len(games) - int(coverage_counts[domain])
        counts[f"{domain}_serialized_rows"] = int(serialized_row_counts[domain])
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_2001_STRUCTURED_DOMAINS_GATE",
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
            "inventory_gate_identity": INVENTORY_GATE_IDENTITY,
            "bat622_gate_identity": PINNED_BAT622_GATE_IDENTITY,
            "bat622_acquisition_identity": PINNED_BAT622_ACQUISITION_IDENTITY,
            "bat622_dataset_identity": PINNED_BAT622_DATASET_IDENTITY,
            "bat622_games_identity": PINNED_BAT622_GAMES_IDENTITY,
            "bat621_gate_identity": PINNED_BAT621_GATE_IDENTITY,
            "bat621_capture_identity": PINNED_BAT621_CAPTURE_IDENTITY,
            "bat621_box_url_identity": PINNED_BAT621_BOX_URL_IDENTITY,
            "bat621_payload_identity": PINNED_BAT621_PAYLOAD_IDENTITY,
            "bat617_gate_identity": PINNED_BAT617_GATE_IDENTITY,
            "bat617_payload_identity": PINNED_BAT617_PAYLOAD_IDENTITY,
            "bat615_gate_identity": PINNED_BAT615_GATE_IDENTITY,
            "bat615_acquisition_identity": PINNED_BAT615_ACQUISITION_IDENTITY,
            "bat615_dataset_identity": PINNED_BAT615_DATASET_IDENTITY,
            "bat615_games_identity": PINNED_BAT615_GAMES_IDENTITY,
            "bat613_gate_identity": PINNED_BAT613_GATE_IDENTITY,
            "bat613_capture_identity": PINNED_BAT613_CAPTURE_IDENTITY,
            "bat613_box_url_identity": PINNED_BAT613_BOX_URL_IDENTITY,
            "bat613_payload_identity": PINNED_BAT613_PAYLOAD_IDENTITY,
            "bat612_gate_identity": PINNED_BAT612_GATE_IDENTITY,
            "bat612_union_identity": PINNED_BAT612_UNION_IDENTITY,
            "bat611_gate_identity": PINNED_BAT611_GATE_IDENTITY,
            "bat611_payload_identity": PINNED_BAT611_PAYLOAD_IDENTITY,
            "bat610_gate_identity": PINNED_BAT610_GATE_IDENTITY,
            "bat609_gate_identity": PINNED_BAT609_GATE_IDENTITY,
            "bat606_gate_identity": PINNED_BAT606_GATE_IDENTITY,
            "bat606_payload_identity": PINNED_BAT606_PAYLOAD_IDENTITY,
            "bat605_gate_identity": PINNED_BAT605_GATE_IDENTITY,
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
        "rich_structured_games": objects["gate"]["counts"]["rich_structured_games"],
        "serialized_rows_total": objects["gate"]["counts"]["serialized_rows_total"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (data_root / CAPTURE_INDEX_RELATIVE).is_file()


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
    if committed.get("result") not in {
        PASS_RESULT,
        "PARTIAL_OFFICIAL_2001_STRUCTURED_DOMAINS",
    }:
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
    for domain in STRUCTURED_DOMAINS:
        if int(counts.get(f"{domain}_present_games") or 0) and not int(
            counts.get(f"{domain}_serialized_rows") or 0
        ):
            raise AuthorityViolation(
                f"PRESENT claimed without serialized {domain} rows"
            )
    for game in committed.get("games") or []:
        if game.get("parser_identity") != PREFORMATTED_PARSER_IDENTITY:
            raise AuthorityViolation("parser identity changed")
        coverage = game.get("domain_coverage") or {}
        row_counts = game.get("row_counts") or {}
        for domain in STRUCTURED_DOMAINS:
            if coverage.get(domain) == "PRESENT" and not int(
                row_counts.get(domain) or 0
            ):
                raise AuthorityViolation(
                    f"PRESENT claimed without serialized {domain} rows"
                )
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    if (committed.get("upstream_identities") or {}).get(
        "bat622_gate_identity"
    ) != PINNED_BAT622_GATE_IDENTITY:
        raise AuthorityViolation("BAT-622 2001 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat621_gate_identity"
    ) != PINNED_BAT621_GATE_IDENTITY:
        raise AuthorityViolation("BAT-621 2001 index identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat617_gate_identity"
    ) != PINNED_BAT617_GATE_IDENTITY:
        raise AuthorityViolation("BAT-617 2002 structured-domain identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat615_gate_identity"
    ) != PINNED_BAT615_GATE_IDENTITY:
        raise AuthorityViolation("BAT-615 2002 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat613_gate_identity"
    ) != PINNED_BAT613_GATE_IDENTITY:
        raise AuthorityViolation("BAT-613 2002 index identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat612_gate_identity"
    ) != PINNED_BAT612_GATE_IDENTITY:
        raise AuthorityViolation("BAT-612 2003 union identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat611_gate_identity"
    ) != PINNED_BAT611_GATE_IDENTITY:
        raise AuthorityViolation("BAT-611 2003 structured-domain identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat610_gate_identity"
    ) != PINNED_BAT610_GATE_IDENTITY:
        raise AuthorityViolation("BAT-610 2003 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat609_gate_identity"
    ) != PINNED_BAT609_GATE_IDENTITY:
        raise AuthorityViolation("BAT-609 2003 index identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat606_gate_identity"
    ) != PINNED_BAT606_GATE_IDENTITY:
        raise AuthorityViolation("BAT-606 2004 structured-domain identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat605_gate_identity"
    ) != PINNED_BAT605_GATE_IDENTITY:
        raise AuthorityViolation("BAT-605 2004 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat601_gate_identity"
    ) != PINNED_BAT601_GATE_IDENTITY:
        raise AuthorityViolation("BAT-601 2005 structured-domain identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat596_gate_identity"
    ) != PINNED_BAT596_GATE_IDENTITY:
        raise AuthorityViolation("BAT-596 2006 structured-domain identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "bat591_gate_identity"
    ) != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if (committed.get("upstream_identities") or {}).get(
        "html_table_classifier_identity"
    ) != PINNED_TABLE_PARSER_IDENTITY:
        raise AuthorityViolation("Cycle #13 HTML-table classifier identity mutated")


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
            "external 2001 structured-domain reconstruction was required but the data root is not mounted"
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
            "committed 2001 structured-domain gate does not match independent reconstruction"
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
    stored_without = {
        key: value for key, value in stored.items() if key != "payload_identity"
    }
    if compute_identity(stored_without, "payload_identity") != stored.get(
        "payload_identity"
    ):
        raise AuthorityViolation(
            "external payload rows were altered while payload_identity was left unchanged"
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
    return Path(
        os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
    )


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
