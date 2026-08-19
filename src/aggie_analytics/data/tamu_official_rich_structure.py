"""Canonical rich-structure classification for official-box and union artifacts.

A game is rich_structured only when at least one independently parsed domain is
present: team_statistics, individual_player_statistics, or play_by_play.
Scoring-summary presence alone does not make a game rich structured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


RICH_STRUCTURE_DOMAINS: tuple[str, ...] = (
    "team_statistics",
    "individual_player_statistics",
    "play_by_play",
)
SCORING_SUMMARY_DOMAIN = "scoring_summary"
PRESENT = "PRESENT"

ACQUISITION_GATE_RELATIVES: tuple[str, ...] = (
    "artifacts/data_lake/tamu_official_pre2010_boxscore_gate.json",
    "artifacts/data_lake/tamu_official_2007_boxscore_gate.json",
    "artifacts/data_lake/tamu_official_2006_boxscore_gate.json",
    "artifacts/data_lake/tamu_official_2005_boxscore_gate.json",
)
UNION_GATE_RELATIVES: tuple[str, ...] = (
    "artifacts/data_lake/tamu_official_gamebook_union_gate.json",
    "artifacts/data_lake/tamu_official_gamebook_union_expanded_gate.json",
    "artifacts/data_lake/tamu_official_gamebook_union_2007_gate.json",
    "artifacts/data_lake/tamu_official_gamebook_union_enriched_gate.json",
    "artifacts/data_lake/tamu_official_gamebook_union_2006_expanded_gate.json",
)


class RichStructureViolation(ValueError):
    """Raised when official-box and union artifacts disagree on rich structure."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def coverage_map(game_or_coverage: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(game_or_coverage, Mapping):
        return {}
    if "domain_coverage" in game_or_coverage:
        coverage = game_or_coverage.get("domain_coverage") or {}
        return coverage if isinstance(coverage, Mapping) else {}
    return game_or_coverage


def is_rich_structured(game_or_coverage: Mapping[str, Any] | None) -> bool:
    coverage = coverage_map(game_or_coverage)
    return any(coverage.get(domain) == PRESENT for domain in RICH_STRUCTURE_DOMAINS)


def scoring_summary_present(game_or_coverage: Mapping[str, Any] | None) -> bool:
    return coverage_map(game_or_coverage).get(SCORING_SUMMARY_DOMAIN) == PRESENT


def classify_games(games: list[Mapping[str, Any]]) -> dict[str, int]:
    rich = sum(1 for game in games if is_rich_structured(game))
    scoring = sum(1 for game in games if scoring_summary_present(game))
    return {
        "rich_structured_games": rich,
        "metadata_only_games": len(games) - rich,
        "scoring_summary_present_games": scoring,
        "game_count": len(games),
    }


def _domain_present_games(gate: Mapping[str, Any], domain: str) -> int | None:
    coverage = gate.get("domain_coverage") or {}
    bucket = coverage.get(domain)
    if not isinstance(bucket, Mapping):
        return None
    present = bucket.get("present_games")
    if present is None:
        present = bucket.get("official_school_present")
    if present is None:
        present = bucket.get("official_pre2010_present")
    if present is None:
        return None
    return int(present)


def _require_int(counts: Mapping[str, Any], key: str, path: str) -> int:
    if key not in counts:
        raise RichStructureViolation(f"{path}: missing counts.{key}")
    return int(counts[key])


def validate_acquisition_gate(path: Path, gate: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    counts = gate.get("counts") or {}
    try:
        rich = _require_int(counts, "rich_structured_games", str(path))
        metadata = _require_int(counts, "metadata_only_games", str(path))
        scoring = _require_int(counts, "scoring_summary_present_games", str(path))
    except RichStructureViolation as exc:
        return [str(exc)]
    normalized = int(counts.get("normalized_games") or 0)
    if rich + metadata != normalized:
        findings.append(
            f"{path}: rich_structured_games ({rich}) + metadata_only_games ({metadata}) != normalized_games ({normalized})"
        )
    scoring_domain = _domain_present_games(gate, SCORING_SUMMARY_DOMAIN)
    if scoring_domain is not None and scoring != scoring_domain:
        findings.append(
            f"{path}: scoring_summary_present_games ({scoring}) != domain_coverage.scoring_summary.present_games ({scoring_domain})"
        )
    rich_domain_present = {
        domain: _domain_present_games(gate, domain) or 0 for domain in RICH_STRUCTURE_DOMAINS
    }
    if sum(rich_domain_present.values()) == 0 and rich != 0:
        findings.append(
            f"{path}: rich_structured_games is {rich} but team_statistics, individual_player_statistics, and play_by_play are all absent"
        )
    if scoring > 0 and rich == scoring and sum(rich_domain_present.values()) == 0:
        findings.append(
            f"{path}: scoring-summary presence alone was treated as rich structure"
        )
    upper = min(normalized, sum(rich_domain_present.values())) if normalized else sum(rich_domain_present.values())
    if rich > upper:
        findings.append(
            f"{path}: rich_structured_games ({rich}) exceeds independently present rich-domain games ({upper})"
        )
    return findings


def _union_game_lists(gate: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in (
        "enriched_official_games",
        "admitted_official_2007_games",
        "admitted_pre2010_games",
        "official_games",
        "official_school_games",
    ):
        rows = gate.get(key)
        if isinstance(rows, list) and rows:
            return [item for item in rows if isinstance(item, Mapping)]
    return []


def validate_union_gate(path: Path, gate: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    games = _union_game_lists(gate)
    if not games:
        return findings
    classified = classify_games(games)
    coverage = gate.get("coverage_by_season") or {}
    if isinstance(coverage, Mapping) and coverage:
        season_rich = 0
        season_meta = 0
        for bucket in coverage.values():
            if isinstance(bucket, Mapping):
                season_rich += int(bucket.get("rich_structured_games") or 0)
                season_meta += int(bucket.get("metadata_only_games") or 0)
        if season_rich != classified["rich_structured_games"] or season_meta != classified["metadata_only_games"]:
            findings.append(
                f"{path}: coverage_by_season rich/metadata "
                f"({season_rich}/{season_meta}) != canonical classification "
                f"({classified['rich_structured_games']}/{classified['metadata_only_games']})"
            )
    for game in games:
        if is_rich_structured(game) and not any(
            coverage_map(game).get(domain) == PRESENT for domain in RICH_STRUCTURE_DOMAINS
        ):
            findings.append(f"{path}: game classified rich without a canonical domain")
        if scoring_summary_present(game) and is_rich_structured(game):
            if not any(coverage_map(game).get(domain) == PRESENT for domain in RICH_STRUCTURE_DOMAINS):
                findings.append(f"{path}: scoring-summary presence alone was treated as rich structure")
    return findings


def validate_rich_structure_artifacts(*, repo_root: Path) -> dict[str, Any]:
    findings: list[str] = []
    inspected: list[str] = []
    for relative in ACQUISITION_GATE_RELATIVES:
        path = repo_root / relative
        if not path.is_file():
            continue
        inspected.append(relative)
        findings.extend(validate_acquisition_gate(path, load_json(path)))
    for relative in UNION_GATE_RELATIVES:
        path = repo_root / relative
        if not path.is_file():
            continue
        inspected.append(relative)
        findings.extend(validate_union_gate(path, load_json(path)))
    if findings:
        raise RichStructureViolation("; ".join(findings))
    return {"result": "PASS", "inspected": inspected, "findings": []}
