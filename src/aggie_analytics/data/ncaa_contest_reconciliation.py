from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


OWNER_RE = re.compile(
    r'<div class="card-header">\s*<img[^>]*alt="([^"]+)"[^>]*All_Logos/sm//(\d+)\.gif',
    re.DOTALL,
)
ROW_RE = re.compile(r'<tr class="underline_rows">(.*?)</tr>', re.DOTALL)
ANY_ROW_RE = re.compile(r'<tr\b[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
DATE_RE = re.compile(r'<td>\s*(\d{2}/\d{2}/\d{4})\s*</td>', re.DOTALL)
FLEXIBLE_DATE_RE = re.compile(
    r'<td\b[^>]*>\s*(\d{2}/\d{2}/\d{4})\s*</td>',
    re.DOTALL | re.IGNORECASE,
)
OPPONENT_RE = re.compile(
    r'([@]?)\s*<a href="/teams/(\d+)"><img[^>]*alt="([^"]+)"',
    re.DOTALL,
)
CONTEST_RE = re.compile(
    r'href="/contests/(\d+)/box_score">\s*([WLT])\s*(\d+)\s*-\s*(\d+)',
    re.DOTALL | re.IGNORECASE,
)
FLEXIBLE_CONTEST_RE = re.compile(
    r'<a\b[^>]*href=["\']/contests/(\d+)/box_score["\'][^>]*>'
    r'\s*([WLT])\s*(\d+)\s*-\s*(\d+)',
    re.DOTALL | re.IGNORECASE,
)
LEGACY_OPPONENT_RE = re.compile(
    r'<a\b[^>]*href=["\']/teams/(\d+)["\'][^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("NCAA contest reconciliation requires the optional data-engineering environment") from exc
    return polars


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_bytes_immutable(payload: bytes, path: Path, *, artifact: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable {artifact} collision: {path}")
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


def _write_parquet_immutable(frame: Any, path: Path) -> None:
    buffer = io.BytesIO()
    frame.write_parquet(buffer, compression="zstd", statistics=True)
    _write_bytes_immutable(buffer.getvalue(), path, artifact="reconciliation payload")


def _payload_schema(pl: Any, name: str) -> dict[str, Any]:
    """Return the stable public schema for every reconciliation payload."""

    schemas = {
        "contest_mappings.parquet": {
            "classification": pl.String, "season": pl.Int64, "ncaa_contest_id": pl.String,
            "canonical_game_id": pl.String, "season_type": pl.String, "week": pl.Int64,
            "canonical_start_utc": pl.String, "canonical_home_team_id": pl.String,
            "canonical_away_team_id": pl.String, "canonical_home_points": pl.Int64,
            "canonical_away_points": pl.Int64, "source_schedule_observation_count": pl.Int64,
            "source_team_season_page_count": pl.Int64, "source_team_season_ids": pl.String,
            "source_page_raw_sha256s": pl.String, "mapping_method": pl.String,
            "name_only_promotion": pl.Boolean, "historical_pit_eligible": pl.Boolean,
            "training_eligible": pl.Boolean, "protected_eligible": pl.Boolean,
        },
        "legacy_schedule_mappings.parquet": {
            "classification": pl.String, "season": pl.Int64,
            "legacy_schedule_pair_identity": pl.String, "ncaa_contest_id": pl.String,
            "canonical_game_id": pl.String, "season_type": pl.String, "week": pl.Int64,
            "canonical_start_utc": pl.String, "canonical_home_team_id": pl.String,
            "canonical_away_team_id": pl.String, "canonical_home_points": pl.Int64,
            "canonical_away_points": pl.Int64, "source_schedule_observation_count": pl.Int64,
            "source_team_season_page_count": pl.Int64, "source_team_season_ids": pl.String,
            "source_page_raw_sha256s": pl.String, "mapping_method": pl.String,
            "contest_id_fabricated": pl.Boolean, "name_only_promotion": pl.Boolean,
            "historical_pit_eligible": pl.Boolean, "training_eligible": pl.Boolean,
            "protected_eligible": pl.Boolean,
        },
        "team_season_mappings.parquet": {
            "classification": pl.String, "season": pl.Int64, "source_team_season_id": pl.String,
            "source_team_org_id": pl.String, "source_team_name": pl.String,
            "source_page_raw_sha256": pl.String, "canonical_team_id": pl.String,
            "supporting_contest_count": pl.Int64, "supporting_ncaa_contest_ids": pl.String,
            "supporting_legacy_game_count": pl.Int64, "supporting_legacy_game_ids": pl.String,
            "mapping_method": pl.String, "name_only_promotion": pl.Boolean,
        },
        "unresolved_contests.parquet": {
            "classification": pl.String, "season": pl.Int64, "ncaa_contest_id": pl.String,
            "reason": pl.String, "source_schedule_observation_count": pl.Int64,
            "candidate_canonical_game_ids": pl.String, "source_team_season_ids": pl.String,
        },
        "unresolved_legacy_schedule_observations.parquet": {
            "classification": pl.String, "season": pl.Int64,
            "legacy_source_row_identity": pl.String, "source_team_season_id": pl.String,
            "opponent_team_season_id": pl.String, "reason": pl.String,
            "candidate_canonical_game_ids": pl.String,
        },
        "source_schedule_observations.parquet": {
            "contest_id": pl.String, "source_team_season_id": pl.String,
            "source_team_org_id": pl.String, "source_team_name": pl.String,
            "source_team_name_normalized": pl.String, "opponent_team_season_id": pl.String,
            "opponent_team_name": pl.String, "opponent_team_name_normalized": pl.String,
            "source_schedule_date": pl.String, "source_team_is_away": pl.Boolean,
            "source_result": pl.String, "source_team_points": pl.Int64,
            "opponent_points": pl.Int64, "source_page_raw_sha256": pl.String,
            "candidate_canonical_game_ids": pl.String, "candidate_count": pl.Int64,
            "candidate_source_team_id": pl.String, "candidate_opponent_team_id": pl.String,
            "participant_aliases_uniquely_resolved": pl.Boolean,
        },
        "legacy_source_schedule_observations.parquet": {
            "legacy_source_row_identity": pl.String, "source_row_sha256": pl.String,
            "contest_id": pl.String, "source_team_season_id": pl.String,
            "source_team_org_id": pl.String, "source_team_name": pl.String,
            "source_team_name_normalized": pl.String, "opponent_team_season_id": pl.String,
            "opponent_team_name": pl.String, "opponent_team_name_normalized": pl.String,
            "source_schedule_date": pl.String, "source_team_is_away": pl.Boolean,
            "source_result": pl.String, "source_result_was_explicit": pl.Boolean,
            "source_team_points": pl.Int64, "opponent_points": pl.Int64,
            "source_page_raw_sha256": pl.String, "candidate_canonical_game_ids": pl.String,
            "candidate_count": pl.Int64, "candidate_source_team_id": pl.String,
            "candidate_opponent_team_id": pl.String,
            "participant_aliases_uniquely_resolved": pl.Boolean,
        },
        "page_parse_failures.parquet": {
            "source_team_season_id": pl.String, "source_page_raw_sha256": pl.String,
            "reason": pl.String,
        },
    }
    return schemas[name]


def _payload_frame(pl: Any, name: str, records: list[dict[str, Any]]) -> Any:
    return pl.DataFrame(records, schema=_payload_schema(pl, name), infer_schema_length=None)


def normalize_team_name(value: str) -> str:
    folded = unicodedata.normalize("NFKD", html.unescape(value)).encode("ascii", "ignore").decode("ascii")
    folded = folded.lower().replace("&", " and ")
    expansions = {"st": "state", "so": "southern"}
    return " ".join(expansions.get(token, token) for token in re.sub(r"[^a-z0-9]+", " ", folded).split())


def _fragment_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", value))).strip()


def _modern_opponent(block: str) -> tuple[str, str, str] | None:
    logo_link = OPPONENT_RE.search(block)
    if logo_link is not None:
        return logo_link.groups()
    text_link = LEGACY_OPPONENT_RE.search(block)
    if text_link is None:
        return None
    opponent_team_season_id, opponent_fragment = text_link.groups()
    opponent_label = _fragment_text(opponent_fragment)
    source_team_is_away = opponent_label.startswith("@")
    opponent_name = (
        opponent_label[1:].strip() if source_team_is_away else opponent_label
    )
    if not opponent_name:
        return None
    return "@" if source_team_is_away else "", opponent_team_season_id, opponent_name


def parse_team_page(payload: str, *, team_season_id: str, raw_sha256: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    owner = OWNER_RE.search(payload)
    if owner is None:
        return None, []
    owner_name, owner_org_id = owner.groups()
    rows: list[dict[str, Any]] = []
    for block in ANY_ROW_RE.findall(payload):
        observed_date = FLEXIBLE_DATE_RE.search(block)
        opponent = _modern_opponent(block)
        contest = FLEXIBLE_CONTEST_RE.search(block)
        if observed_date is None or opponent is None or contest is None:
            continue
        away_marker, opponent_team_season_id, opponent_name = opponent
        contest_id, result, owner_points, opponent_points = contest.groups()
        rows.append({
            "contest_id": contest_id,
            "source_team_season_id": team_season_id,
            "source_team_org_id": owner_org_id,
            "source_team_name": owner_name,
            "source_team_name_normalized": normalize_team_name(owner_name),
            "opponent_team_season_id": opponent_team_season_id,
            "opponent_team_name": opponent_name,
            "opponent_team_name_normalized": normalize_team_name(opponent_name),
            "source_schedule_date": datetime.strptime(observed_date.group(1), "%m/%d/%Y").date().isoformat(),
            "source_team_is_away": away_marker == "@",
            "source_result": result.upper(),
            "source_team_points": int(owner_points),
            "opponent_points": int(opponent_points),
            "source_page_raw_sha256": raw_sha256,
        })
    return {
        "source_team_season_id": team_season_id,
        "source_team_org_id": owner_org_id,
        "source_team_name": owner_name,
        "source_team_name_normalized": normalize_team_name(owner_name),
        "scored_schedule_rows": len(rows),
        "source_page_raw_sha256": raw_sha256,
    }, rows


def parse_legacy_team_page(
    payload: str, *, team_season_id: str, raw_sha256: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Parse pre-contest-link NCAA schedule rows without inventing contest IDs."""

    owner = OWNER_RE.search(payload)
    if owner is None:
        return None, []
    owner_name, owner_org_id = owner.groups()
    rows: list[dict[str, Any]] = []
    for block in ANY_ROW_RE.findall(payload):
        if re.search(r"/contests/\d+/box_score", block, re.IGNORECASE):
            continue
        observed_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", block)
        opponent = LEGACY_OPPONENT_RE.search(block)
        row_text = _fragment_text(block)
        score = re.search(r"\b(?:(W|L|T)\s+)?(\d+)\s*-\s*(\d+)\b", row_text, re.IGNORECASE)
        if observed_date is None or opponent is None or score is None:
            continue
        opponent_team_season_id, opponent_fragment = opponent.groups()
        opponent_label = _fragment_text(opponent_fragment)
        source_team_is_away = opponent_label.startswith("@")
        opponent_name = opponent_label[1:].strip() if source_team_is_away else opponent_label
        if not opponent_name:
            continue
        source_points = int(score.group(2))
        opponent_points = int(score.group(3))
        explicit_result = score.group(1).upper() if score.group(1) else None
        inferred_result = "W" if source_points > opponent_points else "L" if source_points < opponent_points else "T"
        source_row_sha256 = hashlib.sha256(block.encode("utf-8")).hexdigest()
        rows.append({
            "legacy_source_row_identity": stable_hash({
                "source_team_season_id": team_season_id,
                "source_page_raw_sha256": raw_sha256,
                "source_row_sha256": source_row_sha256,
            }),
            "source_row_sha256": source_row_sha256,
            "contest_id": None,
            "source_team_season_id": team_season_id,
            "source_team_org_id": owner_org_id,
            "source_team_name": owner_name,
            "source_team_name_normalized": normalize_team_name(owner_name),
            "opponent_team_season_id": opponent_team_season_id,
            "opponent_team_name": opponent_name,
            "opponent_team_name_normalized": normalize_team_name(opponent_name),
            "source_schedule_date": datetime.strptime(observed_date.group(1), "%m/%d/%Y").date().isoformat(),
            "source_team_is_away": source_team_is_away,
            "source_result": explicit_result or inferred_result,
            "source_result_was_explicit": explicit_result is not None,
            "source_team_points": source_points,
            "opponent_points": opponent_points,
            "source_page_raw_sha256": raw_sha256,
        })
    return {
        "source_team_season_id": team_season_id,
        "source_team_org_id": owner_org_id,
        "source_team_name": owner_name,
        "source_team_name_normalized": normalize_team_name(owner_name),
        "legacy_scored_schedule_rows": len(rows),
        "source_page_raw_sha256": raw_sha256,
    }, rows


def _verify(path: Path, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    if actual.lower() != expected_sha256.lower():
        raise ValueError(f"pinned input drift for {path}: expected {expected_sha256}, found {actual}")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": actual}


def _alias_index(registry_path: Path, season: int) -> dict[str, set[str]]:
    pl = _polars()
    aliases = (
        pl.scan_csv(registry_path, infer_schema_length=0)
        .filter(
            (pl.col("record_type") == "ALIAS")
            & (pl.col("entity_type") == "team")
            & (pl.col("resolution_state") == "AUTO_ACCEPTED_VERIFIED")
        )
        .select("canonical_id", "alias")
        .collect()
    )
    result: dict[str, set[str]] = defaultdict(set)
    for row in aliases.iter_rows(named=True):
        # The alias is only a candidate generator. Admission additionally
        # requires both participant identities, two mirrored NCAA team pages,
        # date, and oriented final score to resolve to one canonical game.
        # Historical alias observation intervals therefore do not, by
        # themselves, grant or deny a mapping.
        result[normalize_team_name(row["alias"])].add(row["canonical_id"])
    return result


def _outcomes(path: Path, season: int) -> list[dict[str, Any]]:
    pl = _polars()
    return (
        pl.read_parquet(path)
        .filter(pl.col("season") == season)
        .select("target_game_id", "season_type", "week", "start_utc", "home_team_id", "away_team_id", "home_points", "away_points")
        .sort(["start_utc", "target_game_id"])
        .to_dicts()
    )


def _candidate_games(
    observation: dict[str, Any], alias_index: dict[str, set[str]], outcomes: Iterable[dict[str, Any]], maximum_date_delta: int
) -> tuple[list[str], str | None, str | None]:
    source_ids = alias_index.get(observation["source_team_name_normalized"], set())
    opponent_ids = alias_index.get(observation["opponent_team_name_normalized"], set())
    if len(source_ids) != 1 or len(opponent_ids) != 1:
        return [], None, None
    source_id = next(iter(source_ids))
    opponent_id = next(iter(opponent_ids))
    observed_date = date.fromisoformat(observation["source_schedule_date"])
    candidates: list[str] = []
    for game in outcomes:
        game_date = datetime.fromisoformat(game["start_utc"].replace("Z", "+00:00")).date()
        if abs((game_date - observed_date).days) > maximum_date_delta:
            continue
        if (
            game["home_team_id"] == source_id
            and game["away_team_id"] == opponent_id
            and int(game["home_points"]) == observation["source_team_points"]
            and int(game["away_points"]) == observation["opponent_points"]
        ) or (
            game["home_team_id"] == opponent_id
            and game["away_team_id"] == source_id
            and int(game["home_points"]) == observation["opponent_points"]
            and int(game["away_points"]) == observation["source_team_points"]
        ):
            candidates.append(game["target_game_id"])
    return sorted(set(candidates)), source_id, opponent_id


def reconcile(*, input_data_root: Path, output_data_root: Path, repo_root: Path, contract_path: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    source = contract["source_contract"]
    season = int(source["season"])
    paths = {
        "discovery_manifest": input_data_root / source["discovery_manifest"],
        "canonical_registry": input_data_root / source["canonical_registry"],
        "outcome_targets": input_data_root / source["outcome_targets"],
    }
    inputs = {name: _verify(path, source[f"{name}_sha256"]) for name, path in paths.items()}
    discovery = json.loads(paths["discovery_manifest"].read_text(encoding="utf-8"))
    if int(discovery["season"]) != season or discovery["state"] != "COMPLETE_GRAPH_EXHAUSTED":
        raise ValueError("discovery manifest is not a complete graph for the contracted season")

    alias_index = _alias_index(paths["canonical_registry"], season)
    outcomes = _outcomes(paths["outcome_targets"], season)
    outcome_by_id = {row["target_game_id"]: row for row in outcomes}
    observations: list[dict[str, Any]] = []
    legacy_observations: list[dict[str, Any]] = []
    page_summaries: list[dict[str, Any]] = []
    page_failures: list[dict[str, Any]] = []
    for capture in sorted(discovery["captures"], key=lambda row: row["team_season_id"]):
        raw_path = input_data_root / capture["raw_relative_path"]
        _verify(raw_path, capture["raw_sha256"])
        raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
        page, rows = parse_team_page(
            raw_text,
            team_season_id=capture["team_season_id"],
            raw_sha256=capture["raw_sha256"],
        )
        if page is None:
            page_failures.append({
                "source_team_season_id": capture["team_season_id"],
                "source_page_raw_sha256": capture["raw_sha256"],
                "reason": "SOURCE_PAGE_OWNER_HEADER_NOT_PARSED",
            })
            continue
        page_summaries.append(page)
        observations.extend(rows)
        _, legacy_rows = parse_legacy_team_page(
            raw_text,
            team_season_id=capture["team_season_id"],
            raw_sha256=capture["raw_sha256"],
        )
        legacy_observations.extend(legacy_rows)

    maximum_date_delta = int(contract["admission"]["maximum_source_date_to_utc_date_delta_days"])
    by_contest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    enriched: list[dict[str, Any]] = []
    for observation in observations:
        candidates, source_team_id, opponent_team_id = _candidate_games(
            observation, alias_index, outcomes, maximum_date_delta
        )
        row = {
            **observation,
            "candidate_canonical_game_ids": ";".join(candidates),
            "candidate_count": len(candidates),
            "candidate_source_team_id": source_team_id,
            "candidate_opponent_team_id": opponent_team_id,
            "participant_aliases_uniquely_resolved": source_team_id is not None and opponent_team_id is not None,
        }
        enriched.append(row)
        by_contest[observation["contest_id"]].append(row)

    mappings: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    all_discovered = set(str(value) for value in discovery["discovered_contest_ids"])
    for contest_id in sorted(all_discovered, key=int):
        rows = by_contest.get(contest_id, [])
        candidates = sorted({candidate for row in rows for candidate in row["candidate_canonical_game_ids"].split(";") if candidate})
        matched_rows = [row for row in rows if row["candidate_count"] == 1 and row["candidate_canonical_game_ids"] in candidates]
        distinct_pages = {row["source_team_season_id"] for row in matched_rows}
        mirrored_pair = False
        if len(candidates) == 1 and len(distinct_pages) >= 2:
            candidate = candidates[0]
            game = outcome_by_id[candidate]
            owner_ids = {row["candidate_source_team_id"] for row in matched_rows}
            mirrored_pair = owner_ids == {game["home_team_id"], game["away_team_id"]}
        if len(candidates) == 1 and len(matched_rows) >= 2 and len(distinct_pages) >= 2 and mirrored_pair:
            game = outcome_by_id[candidates[0]]
            mappings.append({
                "classification": contract["classification"],
                "season": season,
                "ncaa_contest_id": contest_id,
                "canonical_game_id": candidates[0],
                "season_type": game["season_type"],
                "week": game["week"],
                "canonical_start_utc": game["start_utc"],
                "canonical_home_team_id": game["home_team_id"],
                "canonical_away_team_id": game["away_team_id"],
                "canonical_home_points": game["home_points"],
                "canonical_away_points": game["away_points"],
                "source_schedule_observation_count": len(matched_rows),
                "source_team_season_page_count": len(distinct_pages),
                "source_team_season_ids": ";".join(sorted(distinct_pages, key=int)),
                "source_page_raw_sha256s": ";".join(sorted({row["source_page_raw_sha256"] for row in matched_rows})),
                "mapping_method": "TWO_SIDED_EXACT_PARTICIPANTS_DATE_SCORE_CONTEXT",
                "name_only_promotion": False,
                "historical_pit_eligible": False,
                "training_eligible": False,
                "protected_eligible": False,
            })
        else:
            if not rows:
                reason = "NO_COMPLETED_SCORE_OBSERVATION"
            elif not any(row["participant_aliases_uniquely_resolved"] for row in rows):
                reason = "PARTICIPANT_ALIAS_NOT_UNIQUELY_RESOLVED"
            elif not candidates:
                reason = "NO_EXACT_CANONICAL_PARTICIPANT_DATE_SCORE_MATCH"
            elif len(candidates) > 1:
                reason = "CONFLICTING_CANONICAL_CANDIDATES"
            else:
                reason = "INSUFFICIENT_TWO_SIDED_SOURCE_EVIDENCE"
            unresolved.append({
                "classification": "CANDIDATE_ONLY_UNRESOLVED_PRESERVED",
                "season": season,
                "ncaa_contest_id": contest_id,
                "reason": reason,
                "source_schedule_observation_count": len(rows),
                "candidate_canonical_game_ids": ";".join(candidates),
                "source_team_season_ids": ";".join(sorted({row["source_team_season_id"] for row in rows}, key=int)),
            })

    legacy_enriched: list[dict[str, Any]] = []
    legacy_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in legacy_observations:
        candidates, source_team_id, opponent_team_id = _candidate_games(
            observation, alias_index, outcomes, maximum_date_delta
        )
        row = {
            **observation,
            "candidate_canonical_game_ids": ";".join(candidates),
            "candidate_count": len(candidates),
            "candidate_source_team_id": source_team_id,
            "candidate_opponent_team_id": opponent_team_id,
            "participant_aliases_uniquely_resolved": source_team_id is not None and opponent_team_id is not None,
        }
        legacy_enriched.append(row)
        if len(candidates) == 1:
            legacy_by_candidate[candidates[0]].append(row)

    legacy_mappings: list[dict[str, Any]] = []
    accepted_legacy_rows: set[str] = set()
    accepted_modern_games = {row["canonical_game_id"] for row in mappings}
    for candidate in sorted(legacy_by_candidate):
        if candidate in accepted_modern_games:
            continue
        rows = legacy_by_candidate[candidate]
        game = outcome_by_id[candidate]
        mirrored_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for left in rows:
            for right in rows:
                if left["legacy_source_row_identity"] >= right["legacy_source_row_identity"]:
                    continue
                if (
                    left["source_team_season_id"] == right["opponent_team_season_id"]
                    and right["source_team_season_id"] == left["opponent_team_season_id"]
                    and left["source_schedule_date"] == right["source_schedule_date"]
                    and left["source_team_points"] == right["opponent_points"]
                    and left["opponent_points"] == right["source_team_points"]
                ):
                    mirrored_pairs.append((left, right))
        owner_ids = {row["candidate_source_team_id"] for row in rows}
        if len(mirrored_pairs) != 1 or owner_ids != {game["home_team_id"], game["away_team_id"]}:
            continue
        left, right = mirrored_pairs[0]
        pair_identity = stable_hash({
            "canonical_game_id": candidate,
            "source_rows": sorted([left["legacy_source_row_identity"], right["legacy_source_row_identity"]]),
        })
        accepted_legacy_rows.update([left["legacy_source_row_identity"], right["legacy_source_row_identity"]])
        legacy_mappings.append({
            "classification": contract["classification"],
            "season": season,
            "legacy_schedule_pair_identity": pair_identity,
            "ncaa_contest_id": None,
            "canonical_game_id": candidate,
            "season_type": game["season_type"],
            "week": game["week"],
            "canonical_start_utc": game["start_utc"],
            "canonical_home_team_id": game["home_team_id"],
            "canonical_away_team_id": game["away_team_id"],
            "canonical_home_points": game["home_points"],
            "canonical_away_points": game["away_points"],
            "source_schedule_observation_count": 2,
            "source_team_season_page_count": 2,
            "source_team_season_ids": ";".join(sorted({left["source_team_season_id"], right["source_team_season_id"]}, key=int)),
            "source_page_raw_sha256s": ";".join(sorted({left["source_page_raw_sha256"], right["source_page_raw_sha256"]})),
            "mapping_method": "TWO_SIDED_LEGACY_TEAM_LINK_EXACT_PARTICIPANTS_DATE_SCORE_CONTEXT",
            "contest_id_fabricated": False,
            "name_only_promotion": False,
            "historical_pit_eligible": False,
            "training_eligible": False,
            "protected_eligible": False,
        })

    unresolved_legacy: list[dict[str, Any]] = []
    for row in legacy_enriched:
        if row["legacy_source_row_identity"] in accepted_legacy_rows:
            continue
        if not row["participant_aliases_uniquely_resolved"]:
            reason = "PARTICIPANT_ALIAS_NOT_UNIQUELY_RESOLVED"
        elif row["candidate_count"] == 0:
            reason = "NO_EXACT_CANONICAL_PARTICIPANT_DATE_SCORE_MATCH"
        elif row["candidate_count"] > 1:
            reason = "CONFLICTING_CANONICAL_CANDIDATES"
        elif row["candidate_canonical_game_ids"] in accepted_modern_games:
            reason = "DUPLICATE_OF_ACCEPTED_MODERN_CONTEST_MAPPING"
        else:
            reason = "INSUFFICIENT_RECIPROCAL_TWO_SIDED_LEGACY_SOURCE_EVIDENCE"
        unresolved_legacy.append({
            "classification": "CANDIDATE_ONLY_UNRESOLVED_PRESERVED",
            "season": season,
            "legacy_source_row_identity": row["legacy_source_row_identity"],
            "source_team_season_id": row["source_team_season_id"],
            "opponent_team_season_id": row["opponent_team_season_id"],
            "reason": reason,
            "candidate_canonical_game_ids": row["candidate_canonical_game_ids"],
        })

    if len({row["ncaa_contest_id"] for row in mappings}) != len(mappings):
        raise ValueError("NCAA contest mapping is not unique")
    if len({row["canonical_game_id"] for row in mappings}) != len(mappings):
        raise ValueError("canonical game mapping is not one-to-one")
    if len({row["canonical_game_id"] for row in legacy_mappings}) != len(legacy_mappings):
        raise ValueError("legacy canonical game mapping is not one-to-one")
    if accepted_modern_games & {row["canonical_game_id"] for row in legacy_mappings}:
        raise ValueError("canonical game mapped through both modern and legacy NCAA evidence")

    team_support: dict[str, dict[str, Any]] = {}
    accepted_contests = {row["ncaa_contest_id"] for row in mappings}
    for row in enriched:
        if row["contest_id"] not in accepted_contests or row["candidate_source_team_id"] is None:
            continue
        key = row["source_team_season_id"]
        support = team_support.setdefault(key, {
            "classification": contract["classification"],
            "season": season,
            "source_team_season_id": key,
            "source_team_org_id": row["source_team_org_id"],
            "source_team_name": row["source_team_name"],
            "canonical_team_ids": set(),
            "supporting_ncaa_contest_ids": set(),
            "source_page_raw_sha256": row["source_page_raw_sha256"],
        })
        support["canonical_team_ids"].add(row["candidate_source_team_id"])
        support["supporting_ncaa_contest_ids"].add(row["contest_id"])
    accepted_legacy_games = {row["canonical_game_id"] for row in legacy_mappings}
    for row in legacy_enriched:
        candidates = [value for value in row["candidate_canonical_game_ids"].split(";") if value]
        if len(candidates) != 1 or candidates[0] not in accepted_legacy_games or row["candidate_source_team_id"] is None:
            continue
        key = row["source_team_season_id"]
        support = team_support.setdefault(key, {
            "classification": contract["classification"],
            "season": season,
            "source_team_season_id": key,
            "source_team_org_id": row["source_team_org_id"],
            "source_team_name": row["source_team_name"],
            "canonical_team_ids": set(),
            "supporting_ncaa_contest_ids": set(),
            "supporting_legacy_game_ids": set(),
            "source_page_raw_sha256": row["source_page_raw_sha256"],
        })
        support.setdefault("supporting_legacy_game_ids", set()).add(candidates[0])
        support["canonical_team_ids"].add(row["candidate_source_team_id"])
    team_mappings: list[dict[str, Any]] = []
    for key in sorted(team_support, key=int):
        row = team_support[key]
        if len(row["canonical_team_ids"]) != 1:
            continue
        team_mappings.append({
            **{
                name: value
                for name, value in row.items()
                if name not in {
                    "canonical_team_ids",
                    "supporting_ncaa_contest_ids",
                    "supporting_legacy_game_ids",
                }
            },
            "canonical_team_id": next(iter(row["canonical_team_ids"])),
            "supporting_contest_count": len(row["supporting_ncaa_contest_ids"]),
            "supporting_ncaa_contest_ids": ";".join(sorted(row["supporting_ncaa_contest_ids"], key=int)),
            "supporting_legacy_game_count": len(row.get("supporting_legacy_game_ids", set())),
            "supporting_legacy_game_ids": ";".join(sorted(row.get("supporting_legacy_game_ids", set()))),
            "mapping_method": "CONSISTENT_ACCEPTED_TWO_SIDED_CONTEST_OR_LEGACY_SCHEDULE_CONTEXT",
            "name_only_promotion": False,
        })

    code_paths = {
        "contract": contract_path,
        "module": repo_root / "src/aggie_analytics/data/ncaa_contest_reconciliation.py",
        "builder": repo_root / "tools/build_ncaa_contest_reconciliation.py",
    }
    identity_core = {
        "contract_id": contract["contract_id"],
        "season": season,
        "inputs": inputs,
        "code_sha256": {name: sha256_file(path) for name, path in code_paths.items()},
        "population": {
            "discovered_contests": len(all_discovered),
            "captured_team_pages": len(discovery["captures"]),
            "parsed_team_pages": len(page_summaries),
            "page_parse_failures": len(page_failures),
            "scored_schedule_observations": len(enriched),
            "canonical_outcome_games": len(outcomes),
            "reconciled_contests": len(mappings),
            "unresolved_contests": len(unresolved),
            "legacy_schedule_observations": len(legacy_enriched),
            "reconciled_legacy_games": len(legacy_mappings),
            "unresolved_legacy_observations": len(unresolved_legacy),
            "reconciled_team_seasons": len(team_mappings),
        },
        "mapping_records": mappings,
        "legacy_mapping_records": legacy_mappings,
        "team_mapping_records": team_mappings,
        "unresolved_records": unresolved,
        "unresolved_legacy_records": unresolved_legacy,
        "page_parse_failures": page_failures,
    }
    dataset_identity = stable_hash(identity_core)
    feature_root = output_data_root / "canonical/ncaa_contest_reconciliation" / "sha256" / dataset_identity
    feature_root.mkdir(parents=True, exist_ok=True)
    payload_specs = [
        ("contest_mappings.parquet", mappings),
        ("legacy_schedule_mappings.parquet", legacy_mappings),
        ("team_season_mappings.parquet", team_mappings),
        ("unresolved_contests.parquet", unresolved),
        ("unresolved_legacy_schedule_observations.parquet", unresolved_legacy),
        ("source_schedule_observations.parquet", enriched),
        ("legacy_source_schedule_observations.parquet", legacy_enriched),
        ("page_parse_failures.parquet", page_failures),
    ]
    payloads: list[dict[str, Any]] = []
    for name, records in payload_specs:
        path = feature_root / name
        _write_parquet_immutable(_payload_frame(pl, name, records), path)
        payloads.append({"name": name, "rows": len(records), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    reason_counts: dict[str, int] = defaultdict(int)
    for row in unresolved:
        reason_counts[row["reason"]] += 1
    legacy_reason_counts: dict[str, int] = defaultdict(int)
    for row in unresolved_legacy:
        legacy_reason_counts[row["reason"]] += 1
    manifest = {
        "schema_version": contract["schema_version"],
        "artifact_type": "NCAA_OFFICIAL_CONTEST_CANONICAL_RECONCILIATION",
        "classification": contract["classification"],
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "identity_core": identity_core,
        "unresolved_reason_counts": dict(sorted(reason_counts.items())),
        "unresolved_legacy_reason_counts": dict(sorted(legacy_reason_counts.items())),
        "payloads": payloads,
        "authority": contract["authority"],
        "nonclaims": {
            "final_historical_completeness": False,
            "historical_pit_admission": False,
            "protected_performance": False,
            "production_readiness": False,
            "champion": False,
            "tamu_lift": False,
            "bas_or_aggie_excess": False,
        },
    }
    manifest_path = output_data_root / "manifests/ncaa_contest_reconciliation" / "sha256" / dataset_identity / "run_manifest.json"
    _write_bytes_immutable(
        canonical_json_bytes(manifest) + b"\n",
        manifest_path,
        artifact="reconciliation manifest",
    )
    return {
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "feature_root": str(feature_root),
        "population": identity_core["population"],
        "unresolved_reason_counts": dict(sorted(reason_counts.items())),
        "payloads": payloads,
        "manifest": manifest,
    }
