"""Immutable 2000-expanded official union from the BAT-624 2001-expanded predecessor."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2000_boxscores import (
    CONTRACT_RELATIVE as BAT626_CONTRACT_RELATIVE,
    GATE_RELATIVE as BAT626_GATE_RELATIVE,
    reconstruct_objects as reconstruct_bat626,
    validate_artifact as validate_bat626,
)
from aggie_analytics.data.tamu_official_2000_season_index import (
    reconstruct as reconstruct_bat625,
    validate_artifact as validate_bat625,
)
from aggie_analytics.data.tamu_official_2000_structured_domains import (
    CONTRACT_RELATIVE as BAT627_CONTRACT_RELATIVE,
    GATE_RELATIVE as BAT627_GATE_RELATIVE,
    STRUCTURED_DOMAINS as OVERLAY_DOMAINS,
    validate_artifact as validate_bat627,
)
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus_integrity import (
    GATE_RELATIVE as BAT620_GATE_RELATIVE,
    validate_artifact as validate_bat620,
)
from aggie_analytics.data.tamu_official_gamebook_union import REGISTRY_SHA256
from aggie_analytics.data.tamu_official_gamebook_union_2001_expanded import (
    GATE_RELATIVE as BAT624_GATE_RELATIVE,
    union_manifest_path as bat624_union_manifest_path,
    upstream_is_ready as bat624_upstream_is_ready,
    validate_artifact as validate_bat624,
)
from aggie_analytics.data.tamu_official_gamebook_union_2002_expanded import (
    PINNED_UNION_IDENTITY as PINNED_BAT618_UNION_IDENTITY,
    PINNED_UNION_MANIFEST_FILE_SHA256 as PINNED_BAT618_UNION_MANIFEST_FILE_SHA256,
    union_manifest_path as bat618_union_manifest_path,
    upstream_is_ready as bat618_upstream_is_ready,
)
from aggie_analytics.data.tamu_official_gamebook_union_2003_expanded import (
    PINNED_UNION_IDENTITY as PINNED_BAT612_UNION_IDENTITY,
    PINNED_UNION_MANIFEST_FILE_SHA256 as PINNED_BAT612_UNION_MANIFEST_FILE_SHA256,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import (
    ADMITTED_STATUSES,
    COMPACT_FIELDS,
    PRESERVED_REJECTION_URLS,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_integrity_bound import (
    PINNED_BAT591_GATE_IDENTITY,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT596_GATE_IDENTITY,
    PINNED_BAT596_PAYLOAD_IDENTITY,
    PINNED_BAT602_GATE_IDENTITY,
    PINNED_BAT602_UNION_IDENTITY,
    coverage_by_domain,
    coverage_by_season,
)
from aggie_analytics.data.tamu_official_gamebook_union_integrity_complete import (
    PINNED_BAT603_GATE_IDENTITY,
    PINNED_BAT603_UNION_IDENTITY,
    PINNED_BAT607_GATE_IDENTITY,
    PINNED_BAT607_UNION_IDENTITY,
    PINNED_GATE_IDENTITY as PINNED_BAT608_GATE_IDENTITY,
    PINNED_UNION_IDENTITY as PINNED_BAT608_UNION_IDENTITY,
)
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.data.tamu_official_rich_structure import (
    is_rich_structured,
    scoring_summary_present,
)
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_2000_expanded.v1"
VALIDATION_CONTRACT_VERSION = "aggie.data.tamu_official_gamebook_union_2000_expanded.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_2000_expanded_contract.json"
GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_gamebook_union_2000_expanded_gate.json"
)
MODULE_RELATIVE = (
    "src/aggie_analytics/data/tamu_official_gamebook_union_2000_expanded.py"
)
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
CONTRACT_ID = "BAT-628-TAMU-OFFICIAL-GAMEBOOK-UNION-2000-EXPANDED-V1"
DECISION_UNIT = "POST-TASK-SRC014-2000-EXPANDED-ENRICHED-UNION-001"
JIRA_KEY = "BAT-628"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_2000_EXPANDED_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_BAT624_PRESERVED_OFFICIAL_2000_ADDED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
OFFICIAL_2000_INDEX_URL = "https://files.12thman.com/history/football/years/2000.html"
OFFICIAL_2000_EXPECTED = 12
OFFICIAL_2000_ADMITTED_EXPECTED = 9
OFFICIAL_2000_REJECTED_EXPECTED = 3
OFFICIAL_2000_UNMATCHED_URLS = frozenset(
    {
        "https://files.12thman.com/history/football/stats/2000-2001/mfb_426_nd.html",
        "https://files.12thman.com/history/football/stats/2000-2001/mfb_429_tech.html",
        "https://files.12thman.com/history/football/stats/2000-2001/mfb_432_isu.html",
    }
)
PRIOR_UNION_CAPTURED_GAMES = 308
PRIOR_UNION_RICH = 295
PRIOR_UNION_METADATA = 13
PRIOR_ENRICHED_OFFICIAL_GAMES = 105
PRIOR_SCORING = 105
UNION_MANIFEST_NAME = "union_manifest.json"
OKLAHOMA_2002_UNMATCHED_URL = (
    "https://files.12thman.com/history/football/stats/2002-2003/mfb_43_ou.html"
)
FORBIDDEN_UNION_URLS = frozenset(
    PRESERVED_REJECTION_URLS | {OKLAHOMA_2002_UNMATCHED_URL}
)
PINNED_BAT618_GATE_IDENTITY = (
    "f0cfca8cd3dd2025be3e69efe377065750770f2bd0e4ae1c0b4a18d85abd44b7"
)
PINNED_BAT624_UNION_IDENTITY = (
    "cb6ff59928119325851db92e7dd1dfc221923da8c86b895e234f459b6adf63a8"
)
PINNED_BAT624_GATE_IDENTITY = (
    "6a202220816144915474278d15e46a43b2ac5610b6a8d87fdfa7b180b1a41710"
)
PINNED_BAT624_UNION_MANIFEST_FILE_SHA256 = (
    "a8242ab742acf76f2f0805920b264d62e1beabefa10878aed4d590494e1b5d10"
)
PINNED_BAT625_GATE_IDENTITY = (
    "38cf419510306d17c203a660051f96da9e186e275833bb763a517cf735b07546"
)
PINNED_BAT625_CAPTURE_IDENTITY = (
    "9a8066e8877b24490d1911c7d01452ae121b11f08e889e2431f76eb65a942cd9"
)
PINNED_BAT625_BOX_URL_IDENTITY = (
    "bf18094298462f7aa06ab63aec47aee89f10797c6fc16d4d3d968c63474aaddc"
)
PINNED_BAT625_PAYLOAD_IDENTITY = (
    "37257a291547283225fac0f9771607557a789d65f40d64ba7b2fefecfbb0a616"
)
PINNED_BAT626_GATE_IDENTITY = (
    "3f7dbc60a7d21359637d04597629a982180d7f97e4d479ad92134567ceec9f8a"
)
PINNED_BAT626_ACQUISITION_IDENTITY = (
    "3a8092ce4c2fbf5ffc4b7af572f9a6ba8cdc360dec2cb538d55dbf7b3ed5f926"
)
PINNED_BAT626_DATASET_IDENTITY = (
    "5d37f54a95c6c3846aa392e2efc860bf2e3aeb6e1b3d02fee3d698c4473b733c"
)
PINNED_BAT626_GAMES_IDENTITY = (
    "e997834aaa8f32685f933e8a1e682cb86b57911405dafad84b5447221aaedf22"
)
PINNED_BAT627_GATE_IDENTITY = (
    "cc1b76240aaab39f355721ed8499a06db3a2d15fcc9056055a594841fba91268"
)
PINNED_BAT627_PAYLOAD_IDENTITY = (
    "6a806655c2bf1ce33200bdd52e77d7f0423a97306d0042edf9384851dc1d8e06"
)
PINNED_BAT620_GATE_IDENTITY = (
    "c71a05330c37ba245ecc8327e1f127377161e66d6cf3260b1035ce8a78761ff4"
)
PINNED_BAT620_DATASET_IDENTITY = (
    "15ab0d2588bcde97b6c6f31a5dbefe6da302d7ceaf2f3ed2f99814ac96ae1481"
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
PINNED_BAT623_GATE_IDENTITY = (
    "efbd7b1e0d52b99d49066878cd45e9b7768a9288f8ed2fe94891cb402b02a666"
)
PINNED_BAT623_PAYLOAD_IDENTITY = (
    "b26370bb6e369a9f0106407461fd647bae7d5a39ef9a5229b6d1283977b857c6"
)
PINNED_BAT612_GATE_IDENTITY = (
    "50e92663d6dbfd8c6770746c99c857cc9db2f1761714e5124a8334eff384f99f"
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
PINNED_BAT617_GATE_IDENTITY = (
    "d6eca244760bba8963130e070d9ac707cb36af7e715b53e2c3bc60a5bbbed014"
)
PINNED_BAT617_PAYLOAD_IDENTITY = (
    "80cda96dc2c38920323806fbc630e9a5eec40996c05acaaf3b3259f17efffbe2"
)
PINNED_BAT609_GATE_IDENTITY = (
    "1a2b16c74bcfc27ba0afc83611fd817d34aa6a2a71a326fd385721b779d9411e"
)
PINNED_BAT609_CAPTURE_IDENTITY = (
    "253a1065192f2e4aa1fa366d967b5c37c0c9586d9b664a3bf0f16079c5105921"
)
PINNED_BAT609_BOX_URL_IDENTITY = (
    "169ecef65490a5a07889ccd06816fda94db5215e6f1eacf6cb22204286800a99"
)
PINNED_BAT609_PAYLOAD_IDENTITY = (
    "9f58c220fe44e8c75835d0dced6dc6571ee7592249eaa6fa209fa181f25fdfa6"
)
PINNED_BAT610_GATE_IDENTITY = (
    "45329843f7b4683e18c231bbc5c835c7d0e488734d849ea18286d9b098291a13"
)
PINNED_BAT610_ACQUISITION_IDENTITY = (
    "f5c0a2824381669501b7bccaeac18ced85f7c14b570d03e56ea4ebb1e4e08ee0"
)
PINNED_BAT610_DATASET_IDENTITY = (
    "741f92a8b0d3c19fe7fd51033e9ddfb797052a9da4e63a2115839a4617e2c0c5"
)
PINNED_BAT610_GAMES_IDENTITY = (
    "17a9daed972a0fa91e554b33adeaf5027aefa206188fec949a4450e2f8971772"
)
PINNED_BAT611_GATE_IDENTITY = (
    "758ca462a05f9d67ff5017417626eae666902f054037c76207231287cb3f20e9"
)
PINNED_BAT611_PAYLOAD_IDENTITY = (
    "8322e53f3ae4b14f7f85b57e30d32664a07b0d5051d4295af681e71083664bf8"
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
PINNED_BAT605_ACQUISITION_IDENTITY = (
    "7fa30d842696f0e73cc23f53daff1638326d58ce5636b354741eca9cf4c21ad9"
)
PINNED_BAT605_DATASET_IDENTITY = (
    "6670084e2578fa0e0339668a8b4f47eeaba5c1368d91043203ecfeda38f6c96b"
)
PINNED_BAT605_GAMES_IDENTITY = (
    "6f7f6505f8e863daeb8d8b7f662fb0ce455a7cb388379815d7d33734cd97ac9b"
)
PINNED_BAT604_GATE_IDENTITY = (
    "3169f6b14e9f2e78e5af2c3dfa33419d80b37c791968fa39e0ddcf91f3643836"
)
NAME_ONLY_STATUSES = frozenset(
    {
        "MATCHED_OPPONENT_NAME_ONLY",
        "NAME_ONLY",
        "OPPONENT_NAME_ONLY",
    }
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
    "predecessor_union_identity",
    "predecessor_gate_identity",
    "union_identity",
    "validation_contract_version",
    "validator_code_identity",
    "selected_seasons",
    "counts",
    "coverage_by_season",
    "coverage_by_domain",
    "enriched_official_games",
    "preserved_rejections",
    "conflicts",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
    "recomputed_upstream",
)


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


def compute_code_identity(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(b"aggie.union.code_bundle.v1\n")
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


def pinned_union_identity(repo_root: Path) -> str:
    return str(
        load_json(repo_root / CONTRACT_RELATIVE).get("pinned_union_identity") or ""
    )


def pinned_union_manifest_file_sha256(repo_root: Path) -> str:
    return str(
        load_json(repo_root / CONTRACT_RELATIVE).get(
            "pinned_union_manifest_file_sha256"
        )
        or ""
    )


def union_manifest_path(data_root: Path, union_identity: str) -> Path:
    if not union_identity:
        raise AuthorityViolation(
            "union identity is required to locate the external manifest"
        )
    return (
        data_root
        / "features/tamu_official_gamebook_union_2000_expanded/sha256"
        / union_identity
        / UNION_MANIFEST_NAME
    )


def require_authoritative_union_manifest(
    *,
    repo_root: Path,
    data_root: Path,
    expected_payload: Mapping[str, Any],
    union_identity: str,
) -> str:
    path = union_manifest_path(data_root, union_identity)
    identity_dir = path.parent
    if not path.is_file():
        raise AuthorityViolation("authoritative external union manifest is missing")
    extras = sorted(
        item.name for item in identity_dir.iterdir() if item.name != UNION_MANIFEST_NAME
    )
    if extras:
        raise AuthorityViolation("extra union manifests present: " + ", ".join(extras))
    try:
        stored = load_json(path)
    except json.JSONDecodeError as exc:
        raise AuthorityViolation(
            "authoritative external union manifest is truncated or malformed"
        ) from exc
    if stored != expected_payload:
        raise AuthorityViolation(
            "external 2000-expanded union payload does not match reconstruction"
        )
    serialized = json.dumps(expected_payload, indent=2, sort_keys=True) + "\n"
    if path.read_text(encoding="utf-8-sig") != serialized:
        raise AuthorityViolation(
            "external 2000-expanded union payload serialization does not match reconstruction"
        )
    digest = sha256_file(path)
    pinned_identity = pinned_union_identity(repo_root)
    pinned_manifest = pinned_union_manifest_file_sha256(repo_root)
    if pinned_identity and union_identity != pinned_identity:
        raise AuthorityViolation("BAT-628 union identity drifted")
    if pinned_manifest and digest != pinned_manifest:
        raise AuthorityViolation("BAT-628 union manifest file SHA-256 drifted")
    return digest


def recompute_bat622_identities(payload: Mapping[str, Any]) -> dict[str, str]:
    games = list(payload.get("games") or [])
    captures = list(payload.get("captures") or [])
    conflicts = list(payload.get("conflicts") or [])
    return {
        "acquisition_identity": stable_hash(captures),
        "games_identity": stable_hash(games),
        "dataset_identity": stable_hash(
            {"games": games, "captures": captures, "conflicts": conflicts}
        ),
    }


def recompute_bat627_payload_identity(payload: Mapping[str, Any]) -> str:
    return compute_identity(payload, "payload_identity")


def _index_by_url(
    games: list[Mapping[str, Any]], label: str
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for game in games:
        url = str(game.get("url") or "")
        if not url:
            raise AuthorityViolation(f"{label} compact game is missing a URL")
        if url in index:
            raise AuthorityViolation(f"duplicate {label} URL {url}")
        index[url] = dict(game)
    return index


def expected_authority() -> dict[str, bool]:
    return {
        "availability_claim": False,
        "bat_429_ready_or_done": False,
        "bat_523_closed": False,
        "champion_or_production_promotion": False,
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "historical_known_at_from_capture_time": False,
        "name_only_promotion": False,
        "ncaa_contest_identity": False,
        "opponent_name_only_admission": False,
        "prior_enriched_union_mutated_in_place": False,
        "rejected_game_admitted": False,
        "trusted_declared_upstream_identity_only": False,
        "wmt_payload_mutated_in_place": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "bat_429_advanced": False,
        "bat_523_closed": False,
        "bat602_union_rewritten": False,
        "bat603_union_rewritten": False,
        "bat607_union_rewritten": False,
        "bat608_union_rewritten": False,
        "bat612_union_rewritten": False,
        "bat618_union_rewritten": False,
        "bat624_union_rewritten": False,
        "bat620_corpus_rewritten": False,
        "bat615_payload_rewritten": False,
        "bat617_payload_rewritten": False,
        "bat626_payload_rewritten": False,
        "bat627_payload_rewritten": False,
        "champion_or_production_promotion": False,
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "ncaa_contest_ids_invented": False,
        "name_only_promoted": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "rejected_games_admitted": False,
        "wmt_payload_mutated": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_429_reevaluation": "POST-SUBTASK-063_066_069_NOT_INDEPENDENTLY_DONE_VERIFIED",
        "bat_523": "IN_PROGRESS",
        "bat_602_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_603_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_607_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_608_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_612_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_609_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_610_boxscores": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_611_domains": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_613_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_615_boxscores": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_617_domains": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_618_union": "PRESERVED_IMMUTABLE_THROUGH_BAT624_PREDECESSOR",
        "bat_620_corpus": "CONSUMED_AS_STRUCTURED_CONSUMER_AUTHORITY_ONLY",
        "bat_621_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_622_boxscores": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_623_domains": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_624_union": "CONSUMED_AS_2001_EXPANDED_PREDECESSOR_ONLY",
        "bat_625_index": "CONSUMED_OFFICIAL_INDEX_URLS_ONLY",
        "bat_626_boxscores": "INDEPENDENTLY_RECOMPUTED_EXTERNAL_PAYLOAD",
        "bat_627_domains": "INDEPENDENTLY_RECOMPUTED_EXTERNAL_ROW_PAYLOAD",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "CANDIDATE_ONLY",
        "wmt_payload": "PRESERVED_IMMUTABLE",
    }


def compact_official_2000(
    game: Mapping[str, Any], official_index_url: str
) -> dict[str, Any]:
    parent = game.get("parent_url")
    if parent in {None, ""}:
        raise AuthorityViolation("parent_url missing; hardcoded fallback is forbidden")
    if parent != official_index_url:
        raise AuthorityViolation("parent_url does not match BAT-625 official index URL")
    row = {key: game.get(key) for key in COMPACT_FIELDS}
    row["source_season"] = int(
        game.get("source_season") or game.get("football_season") or 0
    )
    row["football_season"] = int(
        game.get("football_season") or game.get("source_season") or 0
    )
    row["official_index_url"] = str(parent)
    row["parent_url"] = str(parent)
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["availability"] = "NOT_ESTABLISHED"
    row["historical_publication_time"] = None
    if row["source_season"] != 2000 or row["football_season"] != 2000:
        raise AuthorityViolation("BAT-626 payload contained a non-2000 game")
    return row


def overlay_2000(
    game: Mapping[str, Any],
    domains: Mapping[str, Any],
    payload_identity: str,
    *,
    prior_rich: bool,
    serialized_row_counts: Mapping[str, int],
) -> dict[str, Any]:
    row = json.loads(json.dumps(game))
    coverage = dict(row.get("domain_coverage") or {})
    row["prior_rich_structured"] = prior_rich
    if str(domains.get("source_sha256") or "") != str(row.get("source_sha256") or ""):
        raise AuthorityViolation(
            f"BAT-627 raw hash does not match admitted 2000 game {row.get('url')}"
        )
    if str(domains.get("url") or "") != str(row.get("url") or ""):
        raise AuthorityViolation(
            f"BAT-627 URL does not match admitted 2000 game {row.get('url')}"
        )
    for domain in OVERLAY_DOMAINS:
        if (domains.get("domain_coverage") or {}).get(domain) == "PRESENT":
            if int(serialized_row_counts.get(domain) or 0) <= 0:
                raise AuthorityViolation(
                    f"PRESENT coverage without serialized {domain} rows"
                )
            coverage[domain] = "PRESENT"
    row["domain_coverage"] = coverage
    row["overlay_applied"] = True
    row["overlay_source"] = "BAT-627-2000-STRUCTURED-DOMAINS-INDEPENDENTLY-VALIDATED"
    row["structured_row_payload_identity"] = payload_identity
    row["structured_row_counts"] = dict(serialized_row_counts)
    row["rich_structured"] = is_rich_structured(row)
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["availability"] = "NOT_ESTABLISHED"
    row["historical_publication_time"] = None
    return row


def _bat626_payload_path(data_root: Path, repo_root: Path) -> Path:
    contract = load_json(repo_root / BAT626_CONTRACT_RELATIVE)
    return (
        data_root
        / contract["payloads"]["normalized_root"]
        / PINNED_BAT626_DATASET_IDENTITY
        / "payload.json"
    )


def _bat627_payload_path(data_root: Path, repo_root: Path) -> Path:
    contract = load_json(repo_root / BAT627_CONTRACT_RELATIVE)
    return (
        data_root
        / contract["payloads"]["enriched_root"]
        / PINNED_BAT627_PAYLOAD_IDENTITY
        / "payload.json"
    )


def validate_bat626_external_payload(
    *,
    repo_root: Path,
    data_root: Path,
    payload: Mapping[str, Any] | None = None,
    allowed_urls: list[str] | None = None,
    official_index_url: str = OFFICIAL_2000_INDEX_URL,
) -> dict[str, Any]:
    path = _bat626_payload_path(data_root, repo_root)
    if payload is None:
        if not path.is_file():
            raise AuthorityViolation("external BAT-626 payload is not mounted")
        payload = load_json(path)
    declared = {
        "acquisition_identity": str(payload.get("acquisition_identity") or ""),
        "games_identity": str(payload.get("games_identity") or ""),
        "dataset_identity": str(payload.get("dataset_identity") or ""),
    }
    recomputed = recompute_bat622_identities(payload)
    if recomputed != declared:
        raise AuthorityViolation(
            "BAT-626 declared identities do not match recomputed payload content"
        )
    committed = load_json(repo_root / BAT626_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT626_GATE_IDENTITY:
        raise AuthorityViolation("BAT-626 2000 acquisition identity rewritten")
    for key, value in recomputed.items():
        if committed.get(key) != value:
            raise AuthorityViolation(
                f"recomputed BAT-626 {key} does not match the committed gate"
            )
        if (
            value
            != {
                "acquisition_identity": PINNED_BAT626_ACQUISITION_IDENTITY,
                "games_identity": PINNED_BAT626_GAMES_IDENTITY,
                "dataset_identity": PINNED_BAT626_DATASET_IDENTITY,
            }[key]
        ):
            raise AuthorityViolation(
                f"recomputed BAT-626 {key} does not match the pinned identity"
            )
    if allowed_urls is None:
        raise AuthorityViolation(
            "BAT-625 official 2000 box URLs were not independently reconstructed"
        )
    if len(allowed_urls) != OFFICIAL_2000_EXPECTED:
        raise AuthorityViolation("BAT-625 did not emit 12 official 2000 box URLs")
    if official_index_url != OFFICIAL_2000_INDEX_URL:
        raise AuthorityViolation("BAT-625 official index URL drifted")
    captures = {
        str(item.get("url") or ""): dict(item)
        for item in (payload.get("captures") or [])
    }
    games = list(payload.get("games") or [])
    if len(games) != OFFICIAL_2000_EXPECTED:
        raise AuthorityViolation(f"expected 12 official 2000 games, found {len(games)}")
    allowed_set = frozenset(allowed_urls)
    if {str(item.get("url") or "") for item in games} != allowed_set:
        raise AuthorityViolation(
            "BAT-626 games are not exactly the BAT-625 official index URLs"
        )
    if set(captures) != allowed_set:
        raise AuthorityViolation(
            "BAT-626 capture membership is not exactly the BAT-625 official index URLs"
        )
    rebuilt: list[dict[str, Any]] = []
    for item in games:
        url = str(item.get("url") or "")
        capture = captures.get(url)
        if capture is None:
            raise AuthorityViolation(
                f"BAT-626 capture missing official 2000 URL: {url}"
            )
        raw_rel = str(capture.get("raw_relative_path") or "")
        raw_path = data_root / raw_rel
        if not raw_path.is_file():
            raise AuthorityViolation(f"raw box-score file missing: {url}")
        recomputed_raw = sha256_file(raw_path)
        declared_raw = str(capture.get("raw_sha256") or "")
        if recomputed_raw != declared_raw:
            raise AuthorityViolation(f"raw box-score hash drifted: {url}")
        if str(item.get("source_sha256") or "") != declared_raw:
            raise AuthorityViolation(
                f"game source SHA does not match capture raw SHA: {url}"
            )
        if str(capture.get("url") or "") != url:
            raise AuthorityViolation(f"capture URL does not match game URL {url}")
        compact = compact_official_2000(item, official_index_url)
        status = str(compact.get("canonical_game_match_status") or "")
        if status in NAME_ONLY_STATUSES:
            raise AuthorityViolation("opponent name alone is not admission")
        rebuilt.append(compact)
    reconstructed = reconstruct_bat626(repo_root=repo_root, data_root=data_root)
    reconstructed_identities = {
        "acquisition_identity": reconstructed["payload"]["acquisition_identity"],
        "games_identity": reconstructed["payload"]["games_identity"],
        "dataset_identity": reconstructed["payload"]["dataset_identity"],
    }
    if reconstructed_identities != recomputed:
        raise AuthorityViolation(
            "BAT-626 payload identities do not match independent raw reconstruction"
        )
    return {
        "payload": dict(payload),
        "identities": recomputed,
        "games": rebuilt,
        "conflicts": [dict(item) for item in (payload.get("conflicts") or [])],
        "file_sha256": sha256_file(path) if path.is_file() else None,
        "path": str(path),
    }


def _serialized_row_counts(game_rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = {domain: 0 for domain in OVERLAY_DOMAINS}
    for row in game_rows:
        domain = str(row.get("domain") or row.get("source_domain") or "")
        if domain in counts:
            counts[domain] += 1
    return counts


def validate_bat627_external_payload(
    *,
    repo_root: Path,
    data_root: Path,
    payload: Mapping[str, Any] | None = None,
    compact_games: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    path = _bat627_payload_path(data_root, repo_root)
    if payload is None:
        if not path.is_file():
            raise AuthorityViolation("external BAT-627 payload is not mounted")
        payload = load_json(path)
    declared = str(payload.get("payload_identity") or "")
    recomputed = recompute_bat627_payload_identity(payload)
    if recomputed != declared:
        raise AuthorityViolation(
            "BAT-627 declared payload identity does not match recomputed payload content"
        )
    committed = load_json(repo_root / BAT627_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT627_GATE_IDENTITY:
        raise AuthorityViolation("BAT-627 2000 structured-domain identity rewritten")
    if (
        committed.get("payload_identity") != recomputed
        or recomputed != PINNED_BAT627_PAYLOAD_IDENTITY
    ):
        raise AuthorityViolation(
            "recomputed BAT-627 payload identity does not match the pinned identity"
        )
    if payload.get("availability_claim") or payload.get("availability") not in {
        None,
        "NOT_ESTABLISHED",
    }:
        raise AuthorityViolation("pregame availability claimed")
    external_games = list(payload.get("games") or [])
    row_groups = list(payload.get("rows") or [])
    if (
        len(external_games) != OFFICIAL_2000_EXPECTED
        or len(row_groups) != OFFICIAL_2000_EXPECTED
    ):
        raise AuthorityViolation("BAT-623 external payload game/row membership drifted")
    compact = (
        compact_games
        if compact_games is not None
        else list(committed.get("games") or [])
    )
    compact_by_url = _index_by_url(compact, "BAT-623-gate")
    validated: dict[str, dict[str, Any]] = {}
    for game, rows in zip(external_games, row_groups):
        url = str(game.get("url") or "")
        gate_game = compact_by_url.get(url)
        if gate_game is None:
            raise AuthorityViolation(f"BAT-623 gate is missing external URL {url}")
        serialized_counts = _serialized_row_counts(list(rows))
        declared_counts = {
            domain: len(game.get(domain) or []) for domain in OVERLAY_DOMAINS
        }
        if serialized_counts != declared_counts or serialized_counts != dict(
            gate_game.get("row_counts") or {}
        ):
            raise AuthorityViolation(f"BAT-623 serialized row counts drifted for {url}")
        if str(game.get("source_sha256") or "") != str(
            gate_game.get("source_sha256") or ""
        ):
            raise AuthorityViolation(f"BAT-623 source SHA drifted for {url}")
        if int(game.get("source_season") or 0) != 2000:
            raise AuthorityViolation(f"BAT-627 source season drifted for {url}")
        game_coverage = {
            domain: (game.get("domain_coverage") or {}).get(domain)
            for domain in OVERLAY_DOMAINS
        }
        for domain in OVERLAY_DOMAINS:
            if (
                game_coverage.get(domain) == "PRESENT"
                and serialized_counts[domain] <= 0
            ):
                raise AuthorityViolation(
                    f"PRESENT coverage with zero serialized {domain} rows"
                )
        for row in rows:
            if row.get("availability") != "NOT_ESTABLISHED" or row.get(
                "availability_claim"
            ):
                raise AuthorityViolation(
                    "participation or membership promoted to availability"
                )
            if not str(row.get("source_url") or "") or not str(
                row.get("source_sha256") or ""
            ):
                raise AuthorityViolation(
                    f"BAT-623 row missing explicit URL/SHA provenance for {url}"
                )
            if str(row.get("source_url") or "") != url:
                raise AuthorityViolation(f"BAT-623 row URL drifted for {url}")
            if str(row.get("source_sha256") or "") != str(
                game.get("source_sha256") or ""
            ):
                raise AuthorityViolation(f"BAT-623 row SHA drifted for {url}")
        validated[url] = {
            "url": url,
            "source_sha256": game.get("source_sha256"),
            "source_season": game.get("source_season"),
            "parser_identity": game.get("parser_identity"),
            "domain_coverage": dict(game.get("domain_coverage") or {}),
            "row_counts": serialized_counts,
            "warnings": list(game.get("warnings") or []),
            "rich_structured": bool(game.get("rich_structured")),
            "rows": list(rows),
        }
    if set(validated) != set(compact_by_url):
        raise AuthorityViolation(
            "BAT-623 external payload URLs do not match the compact gate"
        )
    return {
        "payload": dict(payload),
        "payload_identity": recomputed,
        "games": validated,
        "file_sha256": sha256_file(path) if path.is_file() else None,
        "path": str(path),
    }


def reconstruct_objects(
    *,
    repo_root: Path,
    data_root: Path,
    bat610_payload: Mapping[str, Any] | None = None,
    bat611_payload: Mapping[str, Any] | None = None,
    bat615_payload: Mapping[str, Any] | None = None,
    bat617_payload: Mapping[str, Any] | None = None,
    bat626_payload: Mapping[str, Any] | None = None,
    bat627_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bat626_payload = (
        bat626_payload
        if bat626_payload is not None
        else bat615_payload
        if bat615_payload is not None
        else bat610_payload
    )
    bat627_payload = (
        bat627_payload
        if bat627_payload is not None
        else bat617_payload
        if bat617_payload is not None
        else bat611_payload
    )
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    digest = hashlib.sha256(registry.read_bytes()).hexdigest()
    if digest != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("2000-expanded union contract identity drift")
    predecessor = load_json(repo_root / BAT624_GATE_RELATIVE)
    if predecessor.get("union_identity") != PINNED_BAT624_UNION_IDENTITY:
        raise AuthorityViolation("BAT-624 2001-expanded union identity was rewritten")
    if predecessor.get("gate_identity") != PINNED_BAT624_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-624 2001-expanded union gate identity was rewritten"
        )
    if predecessor.get("predecessor_union_identity") != PINNED_BAT618_UNION_IDENTITY:
        raise AuthorityViolation("BAT-618 2002-expanded union identity was rewritten")
    if predecessor.get("predecessor_gate_identity") != PINNED_BAT618_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-618 2002-expanded union gate identity was rewritten"
        )
    if (
        int(predecessor.get("counts", {}).get("union_captured_games") or 0)
        != PRIOR_UNION_CAPTURED_GAMES
    ):
        raise AuthorityViolation("BAT-624 captured-game count drifted")
    if (
        len(predecessor.get("enriched_official_games") or [])
        != PRIOR_ENRICHED_OFFICIAL_GAMES
    ):
        raise AuthorityViolation("BAT-624 official-school membership drifted")
    if int(predecessor.get("counts", {}).get("official_2001_rejected") or 0) != 0:
        raise AuthorityViolation("BAT-624 official 2001 rejection count drifted")
    if int(predecessor.get("counts", {}).get("official_2001_admitted") or 0) != 12:
        raise AuthorityViolation("BAT-624 official 2001 admission count drifted")
    validate_bat624(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    bat624_manifest = bat624_union_manifest_path(
        data_root, PINNED_BAT624_UNION_IDENTITY
    )
    if not bat624_manifest.is_file():
        raise AuthorityViolation("authoritative external union manifest is missing")
    bat624_manifest_sha = sha256_file(bat624_manifest)
    if bat624_manifest_sha != PINNED_BAT624_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-624 union manifest file SHA-256 drifted")
    if not bat618_upstream_is_ready(data_root):
        raise AuthorityViolation("BAT-618 2002-expanded predecessor is not mounted")
    if not bat618_union_manifest_path(data_root).is_file():
        raise AuthorityViolation("BAT-618 external union manifest is missing")
    bat620_gate = load_json(repo_root / BAT620_GATE_RELATIVE)
    if bat620_gate.get("gate_identity") != PINNED_BAT620_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-620 integrity-complete corpus identity was rewritten"
        )
    if bat620_gate.get("dataset_identity") != PINNED_BAT620_DATASET_IDENTITY:
        raise AuthorityViolation(
            "BAT-620 integrity-complete dataset identity was rewritten"
        )
    validate_bat620(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    validate_bat625(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    bat621 = reconstruct_bat625(repo_root=repo_root, data_root=data_root)
    if bat621["gate"]["gate_identity"] != PINNED_BAT625_GATE_IDENTITY:
        raise AuthorityViolation("BAT-625 2000 index identity rewritten")
    if bat621["gate"]["box_url_identity"] != PINNED_BAT625_BOX_URL_IDENTITY:
        raise AuthorityViolation("BAT-625 box-URL identity rewritten")
    if bat621["gate"]["official_index_url"] != OFFICIAL_2000_INDEX_URL:
        raise AuthorityViolation("BAT-625 official index URL drifted")
    allowed = [str(url) for url in (bat621["gate"].get("box_score_urls") or [])]
    validate_bat626(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    validate_bat627(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    bat622 = validate_bat626_external_payload(
        repo_root=repo_root,
        data_root=data_root,
        payload=bat626_payload,
        allowed_urls=allowed,
        official_index_url=str(bat621["gate"]["official_index_url"]),
    )
    bat623 = validate_bat627_external_payload(
        repo_root=repo_root, data_root=data_root, payload=bat627_payload
    )
    prior_games = [
        json.loads(json.dumps(item))
        for item in (predecessor.get("enriched_official_games") or [])
    ]
    rejected = [
        json.loads(json.dumps(item))
        for item in (predecessor.get("preserved_rejections") or [])
    ]
    rejected_urls = {str(item.get("url") or "") for item in rejected}
    if rejected_urls != PRESERVED_REJECTION_URLS:
        raise AuthorityViolation("the four preserved rejected games drifted")
    prior_by_url = _index_by_url(prior_games, "BAT-624")
    admitted_2000: list[dict[str, Any]] = []
    unmatched_2000: list[dict[str, Any]] = []
    for compact in bat622["games"]:
        url = str(compact["url"])
        if url in rejected_urls or url in FORBIDDEN_UNION_URLS:
            raise AuthorityViolation(
                f"rejected game was presented for 2000 admission: {url}"
            )
        if url in prior_by_url:
            raise AuthorityViolation(f"duplicate union membership for {url}")
        if url not in bat623["games"]:
            raise AuthorityViolation(
                f"BAT-627 domains missing for official 2000 URL {url}"
            )
        status = str(compact.get("canonical_game_match_status") or "")
        if status in NAME_ONLY_STATUSES:
            raise AuthorityViolation("opponent name alone is not admission")
        if status not in ADMITTED_STATUSES:
            unmatched_2000.append(dict(compact))
            continue
        admitted_2000.append(
            overlay_2000(
                compact,
                bat623["games"][url],
                bat623["payload_identity"],
                prior_rich=bool(is_rich_structured(compact)),
                serialized_row_counts=bat623["games"][url]["row_counts"],
            )
        )
    admitted_2000.sort(
        key=lambda item: (item["football_season"], item["calendar_date"], item["url"])
    )
    if len(bat622["games"]) != OFFICIAL_2000_EXPECTED:
        raise AuthorityViolation("official 2000 target count drifted")
    if len(admitted_2000) != OFFICIAL_2000_ADMITTED_EXPECTED:
        raise AuthorityViolation("official 2000 admission count drifted")
    if len(unmatched_2000) != OFFICIAL_2000_EXPECTED - OFFICIAL_2000_ADMITTED_EXPECTED:
        raise AuthorityViolation("official 2000 unmatched count drifted")
    if {
        str(item.get("url") or "") for item in unmatched_2000
    } != OFFICIAL_2000_UNMATCHED_URLS:
        raise AuthorityViolation("official 2000 unmatched membership drifted")
    if OFFICIAL_2000_UNMATCHED_URLS & {
        str(item.get("url") or "") for item in admitted_2000
    }:
        raise AuthorityViolation("unmatched official 2000 URL was admitted")
    official_games = prior_games + admitted_2000
    if (
        len(official_games)
        != PRIOR_ENRICHED_OFFICIAL_GAMES + OFFICIAL_2000_ADMITTED_EXPECTED
    ):
        raise AuthorityViolation("2000-expanded official-school membership drifted")
    if len({item["url"] for item in official_games}) != len(official_games):
        raise AuthorityViolation("duplicate URLs in the expanded union")
    admitted_urls = {str(item.get("url") or "") for item in official_games}
    for url in FORBIDDEN_UNION_URLS:
        if url in admitted_urls:
            raise AuthorityViolation(f"forbidden union URL admitted: {url}")
    if admitted_urls & OFFICIAL_2000_UNMATCHED_URLS:
        raise AuthorityViolation("unmatched official 2000 URL was admitted")
    predecessor_conflict_urls = {
        str(item.get("url") or "") for item in (predecessor.get("conflicts") or [])
    }
    if OKLAHOMA_2002_UNMATCHED_URL not in predecessor_conflict_urls:
        raise AuthorityViolation("Oklahoma unmatched strong-tuple drifted")
    became_rich = sum(
        1
        for item in admitted_2000
        if item["rich_structured"] and not item["prior_rich_structured"]
    )
    new_rich = sum(1 for item in admitted_2000 if item["rich_structured"])
    scoring = sum(1 for item in official_games if scoring_summary_present(item))
    predecessor_counts = dict(predecessor.get("counts") or {})
    date_conflicts = int(predecessor_counts.get("date_conflicts") or 0) + sum(
        1
        for item in admitted_2000
        if item.get("conflict_status") not in {None, "NONE"}
        and "DATE" in str(item.get("conflict_status") or "")
    )
    counts = {
        **predecessor_counts,
        "predecessor_308_union_games_preserved": PRIOR_UNION_CAPTURED_GAMES,
        "official_2000_target_games": OFFICIAL_2000_EXPECTED,
        "official_2000_added": len(admitted_2000),
        "official_2000_admitted": len(admitted_2000),
        "official_2000_rejected": len(unmatched_2000),
        "new_games_added": len(admitted_2000),
        "overlays_applied_this_phase": len(admitted_2000),
        "overlays_became_rich_this_phase": became_rich,
        "union_target_games": PRIOR_UNION_CAPTURED_GAMES + len(admitted_2000),
        "union_captured_games": PRIOR_UNION_CAPTURED_GAMES + len(admitted_2000),
        "rich_structured_games": PRIOR_UNION_RICH + new_rich,
        "metadata_only_games": PRIOR_UNION_METADATA + len(admitted_2000) - new_rich,
        "scoring_summary_present_games": scoring,
        "matched_strong_tuple": int(predecessor_counts.get("matched_strong_tuple") or 0)
        + sum(
            1
            for item in admitted_2000
            if item.get("canonical_game_match_status")
            == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"
        ),
        "date_conflicts": date_conflicts,
        "ncaa_contest_ids_created": 0,
        "duplicates_rejected": 0,
        "unmatched_rejected": 4,
    }
    if (
        counts["union_captured_games"]
        != counts["rich_structured_games"] + counts["metadata_only_games"]
    ):
        raise AuthorityViolation("2000-expanded rich/metadata arithmetic drifted")
    if scoring != PRIOR_SCORING + sum(
        1 for item in admitted_2000 if scoring_summary_present(item)
    ):
        raise AuthorityViolation("2000-expanded scoring-summary count drifted")
    conflicts = [
        json.loads(json.dumps(item)) for item in (predecessor.get("conflicts") or [])
    ]
    conflicts.extend(bat622["conflicts"])
    conflicts.extend(
        {
            "url": item["url"],
            "opponent_candidate": item.get("opponent_candidate"),
            "calendar_date": item.get("calendar_date"),
            "index_date_candidate": item.get("index_date_candidate"),
            "conflict_status": item.get("conflict_status"),
            "match_status": item.get("canonical_game_match_status"),
        }
        for item in list(admitted_2000) + unmatched_2000
        if item.get("conflict_status") not in {None, "NONE"}
    )
    code_identity = compute_code_identity(repo_root)
    recomputed_upstream = {
        "bat618_union_identity": PINNED_BAT618_UNION_IDENTITY,
        "bat618_gate_identity": PINNED_BAT618_GATE_IDENTITY,
        "bat624_union_identity": PINNED_BAT624_UNION_IDENTITY,
        "bat624_gate_identity": PINNED_BAT624_GATE_IDENTITY,
        "bat624_union_manifest_file_sha256": bat624_manifest_sha,
        "bat620_gate_identity": PINNED_BAT620_GATE_IDENTITY,
        "bat620_dataset_identity": PINNED_BAT620_DATASET_IDENTITY,
        "bat626_acquisition_identity": bat622["identities"]["acquisition_identity"],
        "bat626_dataset_identity": bat622["identities"]["dataset_identity"],
        "bat626_games_identity": bat622["identities"]["games_identity"],
        "bat626_payload_file_sha256": bat622["file_sha256"],
        "bat627_payload_identity": bat623["payload_identity"],
        "bat627_payload_file_sha256": bat623["file_sha256"],
        "validator_code_identity": code_identity,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": PINNED_BAT624_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT624_GATE_IDENTITY,
        "bat627_payload_identity": bat623["payload_identity"],
        "enriched_official_games": official_games,
        "admitted_official_2000_games": admitted_2000,
        "rejected_official_2000_games": unmatched_2000,
        "preserved_rejections": rejected,
        "counts": counts,
        "conflicts": conflicts,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "recomputed_upstream": recomputed_upstream,
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": PINNED_BAT624_UNION_IDENTITY,
            "predecessor_gate_identity": PINNED_BAT624_GATE_IDENTITY,
            "recomputed_bat626_identities": bat622["identities"],
            "recomputed_bat627_payload_identity": bat623["payload_identity"],
            "upstream_payload_file_hashes": {
                "bat624_union_manifest": bat624_manifest_sha,
                "bat626": bat622["file_sha256"],
                "bat627": bat623["file_sha256"],
            },
            "validator_code_identity": code_identity,
            "validation_contract_version": VALIDATION_CONTRACT_VERSION,
            "admitted_official_2000_games": admitted_2000,
            "rejected_official_2000_games": unmatched_2000,
            "preserved_rejections": rejected,
            "counts": counts,
        }
    )
    predecessor_upstream = dict(predecessor.get("upstream_identities") or {})
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_2000_EXPANDED_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "NEW_IMMUTABLE_IDENTITY_BAT624_PRESERVED_OFFICIAL_2000_ADDED",
        "source_id": SOURCE_ID,
        "predecessor_union_identity": PINNED_BAT624_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT624_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": code_identity,
        "selected_seasons": [
            2009,
            2008,
            2007,
            2006,
            2005,
            2004,
            2003,
            2002,
            2001,
            2000,
        ],
        "counts": counts,
        "coverage_by_season": coverage_by_season(official_games),
        "coverage_by_domain": coverage_by_domain(official_games),
        "enriched_official_games": official_games,
        "admitted_official_2000_games": admitted_2000,
        "rejected_official_2000_games": unmatched_2000,
        "preserved_rejections": rejected,
        "conflicts": conflicts,
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "recomputed_upstream": recomputed_upstream,
        "upstream_identities": {
            **predecessor_upstream,
            "bat612_gate_identity": PINNED_BAT612_GATE_IDENTITY,
            "bat612_union_identity": PINNED_BAT612_UNION_IDENTITY,
            "bat612_union_manifest_file_sha256": PINNED_BAT612_UNION_MANIFEST_FILE_SHA256,
            "bat618_gate_identity": PINNED_BAT618_GATE_IDENTITY,
            "bat618_union_identity": PINNED_BAT618_UNION_IDENTITY,
            "bat618_union_manifest_file_sha256": PINNED_BAT618_UNION_MANIFEST_FILE_SHA256,
            "bat620_gate_identity": PINNED_BAT620_GATE_IDENTITY,
            "bat620_dataset_identity": PINNED_BAT620_DATASET_IDENTITY,
            "bat621_box_url_identity": PINNED_BAT621_BOX_URL_IDENTITY,
            "bat621_capture_identity": PINNED_BAT621_CAPTURE_IDENTITY,
            "bat621_gate_identity": PINNED_BAT621_GATE_IDENTITY,
            "bat621_payload_identity": PINNED_BAT621_PAYLOAD_IDENTITY,
            "bat622_acquisition_identity": PINNED_BAT622_ACQUISITION_IDENTITY,
            "bat622_dataset_identity": PINNED_BAT622_DATASET_IDENTITY,
            "bat622_games_identity": PINNED_BAT622_GAMES_IDENTITY,
            "bat622_gate_identity": PINNED_BAT622_GATE_IDENTITY,
            "bat623_gate_identity": PINNED_BAT623_GATE_IDENTITY,
            "bat623_payload_identity": PINNED_BAT623_PAYLOAD_IDENTITY,
            "bat624_gate_identity": PINNED_BAT624_GATE_IDENTITY,
            "bat624_union_identity": PINNED_BAT624_UNION_IDENTITY,
            "bat624_union_manifest_file_sha256": PINNED_BAT624_UNION_MANIFEST_FILE_SHA256,
            "bat625_box_url_identity": PINNED_BAT625_BOX_URL_IDENTITY,
            "bat625_capture_identity": PINNED_BAT625_CAPTURE_IDENTITY,
            "bat625_gate_identity": PINNED_BAT625_GATE_IDENTITY,
            "bat625_payload_identity": PINNED_BAT625_PAYLOAD_IDENTITY,
            "bat626_acquisition_identity": PINNED_BAT626_ACQUISITION_IDENTITY,
            "bat626_dataset_identity": PINNED_BAT626_DATASET_IDENTITY,
            "bat626_games_identity": PINNED_BAT626_GAMES_IDENTITY,
            "bat626_gate_identity": PINNED_BAT626_GATE_IDENTITY,
            "bat627_gate_identity": PINNED_BAT627_GATE_IDENTITY,
            "bat627_payload_identity": PINNED_BAT627_PAYLOAD_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    if counts["ncaa_contest_ids_created"] or any(
        item.get("ncaa_contest_id") for item in official_games
    ):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(item.get("availability_claim") for item in official_games):
        raise AuthorityViolation("pregame availability claimed")
    if any(
        item.get("historical_publication_time") is not None for item in official_games
    ):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if any(
        item.get("structured_row_payload_identity") != bat623["payload_identity"]
        for item in admitted_2000
    ):
        raise AuthorityViolation(
            "2000 overlay is not bound to the independently recomputed BAT-627 payload identity"
        )
    gate["gate_identity"] = compute_gate_identity(gate)
    payload["gate_identity"] = gate["gate_identity"]
    return {
        "contract": contract,
        "gate": gate,
        "payload": payload,
        "predecessor": predecessor,
        "bat621": bat621,
        "bat622": bat622,
        "bat623": bat623,
        "bat609": bat621,
        "bat610": bat622,
        "bat611": bat623,
    }


def materialize_union(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = (
        data_root
        / objects["contract"]["payloads"]["union_root"]
        / payload["union_identity"]
    )
    write_json(root / "union_manifest.json", payload)
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "union_identity": payload["union_identity"],
        "counts": objects["gate"]["counts"],
        "recomputed_upstream": objects["gate"]["recomputed_upstream"],
    }


def upstream_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    del repo_root
    return (
        bat624_upstream_is_ready(data_root)
        and bat624_union_manifest_path(
            data_root, PINNED_BAT624_UNION_IDENTITY
        ).is_file()
        and (
            data_root
            / "features/tamu_official_2000_boxscores/sha256"
            / PINNED_BAT626_DATASET_IDENTITY
            / "payload.json"
        ).is_file()
        and (
            data_root
            / "features/tamu_official_2000_structured_domains/sha256"
            / PINNED_BAT627_PAYLOAD_IDENTITY
            / "payload.json"
        ).is_file()
    )


def lake_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    if not upstream_is_ready(data_root, repo_root):
        return False
    identity = ""
    if repo_root is not None:
        identity = pinned_union_identity(repo_root)
        if not identity:
            gate_path = repo_root / GATE_RELATIVE
            if gate_path.is_file():
                identity = str(load_json(gate_path).get("union_identity") or "")
    return bool(identity) and union_manifest_path(data_root, identity).is_file()


def validate_compact_gate(
    committed: Mapping[str, Any], repo_root: Path | None = None
) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("predecessor_union_identity") != PINNED_BAT624_UNION_IDENTITY:
        raise AuthorityViolation("BAT-624 2001-expanded union identity was rewritten")
    if committed.get("predecessor_gate_identity") != PINNED_BAT624_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-624 2001-expanded union gate identity was rewritten"
        )
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("completion forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification forged")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("authority", {}).get("opponent_name_only_admission"):
        raise AuthorityViolation("opponent name alone is not admission")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if (
        int((committed.get("counts") or {}).get("new_games_added", -1))
        != OFFICIAL_2000_ADMITTED_EXPECTED
    ):
        raise AuthorityViolation("2000 admission count drifted")
    if (
        int((committed.get("counts") or {}).get("official_2000_rejected") or 0)
        != OFFICIAL_2000_REJECTED_EXPECTED
    ):
        raise AuthorityViolation("official 2000 unmatched rejection count drifted")
    if int((committed.get("counts") or {}).get("official_2001_rejected") or 0) != 0:
        raise AuthorityViolation("official 2001 unmatched rejection count drifted")
    if int((committed.get("counts") or {}).get("official_2002_rejected") or 0) != 1:
        raise AuthorityViolation("official 2002 unmatched rejection count drifted")
    if committed.get("admissions", {}).get("pregame_availability") != "BLOCKED":
        raise AuthorityViolation("pregame availability admitted")
    if (
        committed.get("admissions", {}).get("bat_429")
        != "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES"
    ):
        raise AuthorityViolation(
            "BAT-429 advanced without independently DONE/VERIFIED hard dependencies"
        )
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if (
        int(committed.get("counts", {}).get("union_captured_games") or 0)
        != PRIOR_UNION_CAPTURED_GAMES + OFFICIAL_2000_ADMITTED_EXPECTED
    ):
        raise AuthorityViolation("union captured-game arithmetic drifted")
    rejected_urls = {
        str(item.get("url") or "")
        for item in committed.get("preserved_rejections") or []
    }
    admitted_urls = {
        str(item.get("url") or "")
        for item in committed.get("enriched_official_games") or []
    }
    if rejected_urls != PRESERVED_REJECTION_URLS:
        raise AuthorityViolation("the four preserved rejected games drifted")
    if rejected_urls & admitted_urls:
        raise AuthorityViolation("rejected games were admitted")
    for url in FORBIDDEN_UNION_URLS:
        if url in admitted_urls:
            raise AuthorityViolation(
                "unmatched Oklahoma 2002 box was admitted"
                if url == OKLAHOMA_2002_UNMATCHED_URL
                else "rejected games were admitted"
            )
    if admitted_urls & OFFICIAL_2000_UNMATCHED_URLS:
        raise AuthorityViolation("unmatched official 2000 URL was admitted")
    if any(
        item.get("availability_claim")
        for item in committed.get("enriched_official_games") or []
    ):
        raise AuthorityViolation("pregame availability claimed")
    if any(
        item.get("ncaa_contest_id")
        for item in committed.get("enriched_official_games") or []
    ):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat608_union_identity") != PINNED_BAT608_UNION_IDENTITY:
        raise AuthorityViolation(
            "BAT-608 integrity-complete union identity was rewritten"
        )
    if upstream.get("bat612_union_identity") != PINNED_BAT612_UNION_IDENTITY:
        raise AuthorityViolation("BAT-612 2003-expanded union identity was rewritten")
    if upstream.get("bat618_union_identity") != PINNED_BAT618_UNION_IDENTITY:
        raise AuthorityViolation("BAT-618 2002-expanded union identity was rewritten")
    if upstream.get("bat624_union_identity") != PINNED_BAT624_UNION_IDENTITY:
        raise AuthorityViolation("BAT-624 2001-expanded union identity was rewritten")
    if upstream.get("bat620_gate_identity") != PINNED_BAT620_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-620 integrity-complete corpus identity was rewritten"
        )
    if upstream.get("bat622_gate_identity") != PINNED_BAT622_GATE_IDENTITY:
        raise AuthorityViolation("BAT-622 2001 acquisition identity rewritten")
    if upstream.get("bat623_payload_identity") != PINNED_BAT623_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-623 2001 structured-domain identity rewritten")
    if upstream.get("bat626_gate_identity") != PINNED_BAT626_GATE_IDENTITY:
        raise AuthorityViolation("BAT-626 2000 acquisition identity rewritten")
    if upstream.get("bat627_payload_identity") != PINNED_BAT627_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-627 2000 structured-domain identity rewritten")
    if upstream.get("bat617_payload_identity") != PINNED_BAT617_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-617 2002 structured-domain identity rewritten")
    if upstream.get("bat607_union_identity") != PINNED_BAT607_UNION_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union identity was rewritten")
    if upstream.get("bat603_union_identity") != PINNED_BAT603_UNION_IDENTITY:
        raise AuthorityViolation("BAT-603 integrity-bound union identity was rewritten")
    if upstream.get("bat602_union_identity") != PINNED_BAT602_UNION_IDENTITY:
        raise AuthorityViolation("BAT-602 2005-expanded union identity was rewritten")
    if upstream.get("bat608_gate_identity") != PINNED_BAT608_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-608 integrity-complete union gate identity was rewritten"
        )
    if upstream.get("bat607_gate_identity") != PINNED_BAT607_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-607 2004-expanded union gate identity was rewritten"
        )
    if upstream.get("bat603_gate_identity") != PINNED_BAT603_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-603 integrity-bound union gate identity was rewritten"
        )
    if upstream.get("bat602_gate_identity") != PINNED_BAT602_GATE_IDENTITY:
        raise AuthorityViolation(
            "BAT-602 2005-expanded union gate identity was rewritten"
        )
    if upstream.get("bat591_gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 identity was rewritten")
    if upstream.get("bat591_payload_identity") != PINNED_BAT591_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-591 payload identity was rewritten")
    if upstream.get("bat596_gate_identity") != PINNED_BAT596_GATE_IDENTITY:
        raise AuthorityViolation("BAT-596 identity was rewritten")
    if upstream.get("bat596_payload_identity") != PINNED_BAT596_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-596 payload identity was rewritten")
    if repo_root is not None and committed.get(
        "validator_code_identity"
    ) != compute_code_identity(repo_root):
        raise AuthorityViolation("stale validator code identity")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
    bat610_payload: Mapping[str, Any] | None = None,
    bat611_payload: Mapping[str, Any] | None = None,
    bat615_payload: Mapping[str, Any] | None = None,
    bat617_payload: Mapping[str, Any] | None = None,
    bat626_payload: Mapping[str, Any] | None = None,
    bat627_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed, repo_root)
    ready = upstream_is_ready(data_root, repo_root)
    if require_rebuild and not ready:
        raise AuthorityViolation(
            "external 2000-expanded reconstruction was required but the data root is not mounted"
        )
    payload_622 = (
        bat626_payload
        if bat626_payload is not None
        else bat615_payload
        if bat615_payload is not None
        else bat610_payload
    )
    payload_623 = (
        bat627_payload
        if bat627_payload is not None
        else bat617_payload
        if bat617_payload is not None
        else bat611_payload
    )
    if not ready and payload_622 is None and payload_623 is None:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(
        repo_root=repo_root,
        data_root=data_root,
        bat626_payload=payload_622,
        bat627_payload=payload_623,
    )
    if committed != expected["gate"]:
        raise AuthorityViolation(
            "committed 2000-expanded union gate does not match independent reconstruction"
        )
    require_authoritative_union_manifest(
        repo_root=repo_root,
        data_root=data_root,
        expected_payload=expected["payload"],
        union_identity=str(expected["payload"]["union_identity"]),
    )
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "union_identity": expected["gate"]["union_identity"],
        "counts": expected["gate"]["counts"],
        "recomputed_upstream": expected["gate"]["recomputed_upstream"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(
        os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
    )
