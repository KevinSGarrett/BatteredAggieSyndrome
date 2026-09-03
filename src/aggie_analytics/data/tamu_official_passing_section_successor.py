"""Immutable successor for R26-21 passing-section mislabels.

Predecessor 1996-2009 player rows are never rewritten. Confirmed passing-section
rows receive a new content-addressed successor with corrected stat_group.
Unresolved screen candidates stay unresolved. TEAM rows stay team-attributed
evidence, never fabricated person identities. Header-only tables are not
material statistic availability.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "aggie.data.tamu_official_passing_section_successor.v1"
CONTRACT_ID = "CYCLE26-TAMU-OFFICIAL-PASSING-SECTION-SUCCESSOR-V1"
JIRA_KEY = "BAT-692"
LOCAL_ISSUE_ID = "POST-TASK-SRC014-PASSING-SECTION-SUCCESSOR-001"
CLASSIFICATION = "TAMU_SRC014_PASSING_SECTION_SUCCESSOR_CANDIDATE_ONLY"
LANE = "DEVELOPMENT_SUCCESSOR_UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_PASSING_SECTION_SUCCESSOR"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_passing_section_successor_gate.json"
PAYLOAD_SLUG = "tamu_official_passing_section_successor"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"

PREDECESSOR_PLAYER_RELATIVE = (
    "features/tamu_official_1996_2009_structured_row_corpus/sha256/"
    "7a7f9797bbbc43f273e357584a16ece7715c6ab227438b13fa65775c3dd912f7/"
    "individual_player_statistics.jsonl"
)
PREDECESSOR_PLAYER_SHA256 = (
    "8de41e750e459d592e86768d723883a7fa92f9fea46b3418bf6a805dcb6eecd0"
)
RAW_BOX_DIR = (
    "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/box_scores"
)

EXPECTED_CONFIRMED_ROWS = 429
EXPECTED_AFFECTED_RAW_PAGES = 125

PASSING_HEADER_RE = re.compile(r"^Passing\s+(?:Att|Cmp|No)\b", re.I)
RUSH_RECV_HEADER_RE = re.compile(r"^(?:Rushing|Receiving)\s+No\.?\b", re.I)
OTHER_IND_HEADER_RE = re.compile(
    r"^(?:Punting|Punt Returns|Kickoff Returns|Kick Returns|Interceptions|"
    r"Field Goals|Field goal|Kicking|Kickoffs|Fumbles|Defensive Statistics)\b",
    re.I,
)
TRIPLE_RE = re.compile(r"\b\d+-\d+-\d+\b")


class PassingSectionSuccessorError(ValueError):
    """Raised when the passing-section successor cannot be materialized honestly."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    lines = [
        json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        for row in rows
    ]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def load_predecessor_rows(data_root: Path) -> tuple[list[dict[str, Any]], str, int]:
    path = data_root / PREDECESSOR_PLAYER_RELATIVE
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != PREDECESSOR_PLAYER_SHA256:
        raise PassingSectionSuccessorError(
            f"predecessor player payload rewritten: {digest}"
        )
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return rows, digest, len(raw)


def _clean_line(text: str) -> str:
    return " ".join(text.split())


def screen_nonpassing_triple_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    screened: list[dict[str, Any]] = []
    for row in rows:
        if row.get("stat_group") == "passing":
            continue
        original = row.get("original_text") or ""
        if TRIPLE_RE.search(original):
            screened.append(dict(row))
    return screened


def section_map_from_raw_html(raw: bytes) -> dict[str, set[str | None]]:
    text = html.unescape(re.sub(r"<[^>]*>", "", raw.decode("utf-8", errors="replace")))
    sections: dict[str, set[str | None]] = defaultdict(set)
    section: str | None = None
    for line in text.splitlines():
        clean = _clean_line(line)
        if PASSING_HEADER_RE.match(clean):
            section = "passing"
        elif RUSH_RECV_HEADER_RE.match(clean):
            section = "other"
        elif OTHER_IND_HEADER_RE.match(clean):
            section = "other"
        if clean:
            sections[clean].add(section)
    return sections


def classify_screened_row(
    row: Mapping[str, Any], sections: Mapping[str, set[str | None]]
) -> str:
    clean = _clean_line(str(row.get("original_text") or ""))
    observed = sections.get(clean, set())
    if observed == {"passing"}:
        return "CONFIRMED_PASSING_SECTION_CORRECTION"
    return "UNRESOLVED_AMBIGUOUS_SECTION"


def player_identity_role(row: Mapping[str, Any]) -> str:
    name = str(row.get("name_raw") or "").strip()
    if name.casefold() == "team":
        return "TEAM_ATTRIBUTED_EVIDENCE"
    if not name:
        return "HEADER_OR_EMPTY_NAME"
    return "SOURCE_PLAYER_CANDIDATE_UNMERGED"


def census_predecessor(data_root: Path) -> dict[str, Any]:
    rows, digest, size = load_predecessor_rows(data_root)
    screened = screen_nonpassing_triple_rows(rows)
    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in screened:
        by_sha[str(row["source_sha256"])].append(row)
    confirmed: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    raw_hashes: list[str] = []
    for raw_sha, source_rows in sorted(by_sha.items()):
        path = data_root / RAW_BOX_DIR / f"sha256_{raw_sha}.html"
        raw = path.read_bytes()
        observed = sha256_bytes(raw)
        if observed != raw_sha:
            raise PassingSectionSuccessorError(f"raw hash mismatch: {path}")
        raw_hashes.append(raw_sha)
        sections = section_map_from_raw_html(raw)
        for row in source_rows:
            state = classify_screened_row(row, sections)
            if state == "CONFIRMED_PASSING_SECTION_CORRECTION":
                confirmed.append(dict(row))
            else:
                unresolved.append(
                    {
                        "row_identity": row.get("row_identity"),
                        "source_sha256": raw_sha,
                        "observed_sections": sorted(
                            str(value)
                            for value in sections.get(
                                _clean_line(str(row.get("original_text") or "")),
                                set(),
                            )
                        ),
                    }
                )
    return {
        "predecessor_relative_path": PREDECESSOR_PLAYER_RELATIVE,
        "predecessor_sha256": digest,
        "predecessor_bytes": size,
        "all_player_rows": len(rows),
        "screened_nonpassing_triple_rows": len(screened),
        "confirmed_mislabeled_passing_rows": len(confirmed),
        "unresolved_section_matches": len(unresolved),
        "verified_screened_raw_files": len(raw_hashes),
        "confirmed_affected_raw_files": len(
            {str(row["source_sha256"]) for row in confirmed}
        ),
        "counts_by_season": dict(
            sorted(Counter(str(row.get("season")) for row in confirmed).items())
        ),
        "confirmed_row_identities": [row.get("row_identity") for row in confirmed],
        "unresolved_identities": unresolved,
        "team_pseudo_player_rows": sum(
            player_identity_role(row) == "TEAM_ATTRIBUTED_EVIDENCE" for row in rows
        ),
        "rows": rows,
        "confirmed_rows": confirmed,
        "national_forecast_consumption_proven": False,
    }


def succeed_row(
    row: Mapping[str, Any],
    *,
    confirmed_ids: set[str],
    unresolved_ids: set[str],
) -> dict[str, Any]:
    identity = str(row.get("row_identity") or "")
    predecessor_group = row.get("stat_group")
    if identity in confirmed_ids:
        attribution = "CONFIRMED_PASSING_SECTION_CORRECTION"
        successor_group = "passing"
    elif identity in unresolved_ids:
        attribution = "UNRESOLVED_AMBIGUOUS_SECTION"
        successor_group = predecessor_group
    else:
        attribution = "UNCHANGED"
        successor_group = predecessor_group
    successor = dict(row)
    successor["predecessor_stat_group"] = predecessor_group
    successor["stat_group"] = successor_group
    successor["attribution_state"] = attribution
    successor["player_identity_role"] = player_identity_role(row)
    successor["original_text_preserved"] = row.get("original_text")
    successor["raw_section_text"] = row.get("original_text")
    successor["header_only"] = bool(row.get("header_only"))
    successor["material_statistic_available"] = (
        not bool(row.get("header_only")) and successor_group is not None
    )
    successor["successor_contract_id"] = CONTRACT_ID
    successor["predecessor_rewritten"] = False
    successor["trust_classification"] = SHADOW_CLASSIFICATION
    if player_identity_role(row) == "TEAM_ATTRIBUTED_EVIDENCE":
        successor["fabricated_person_identity"] = False
    return successor


def active_path_join_audit(repo_root: Path) -> dict[str, Any]:
    week1 = (
        repo_root
        / "src"
        / "aggie_analytics"
        / "data"
        / "week1_2026_game_grain_national_forecast_successor.py"
    )
    text = week1.read_text(encoding="utf-8")
    needles = (
        "tamu_official_statcrew_preformatted",
        "tamu_official_1996_2009_structured_row_corpus",
        "individual_player_statistics.jsonl",
        "BAT591",
        "statcrew_preformatted",
    )
    hits = [needle for needle in needles if needle in text]
    return {
        "week1_successor_path": str(week1.as_posix()),
        "needles_present": hits,
        "active_path_import_edges": len(hits),
        "national_forecast_consumption_proven": False,
    }


def build_successor(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    census = census_predecessor(data_root)
    confirmed_count = int(census["confirmed_mislabeled_passing_rows"])
    page_count = int(census["confirmed_affected_raw_files"])
    if confirmed_count != EXPECTED_CONFIRMED_ROWS:
        raise PassingSectionSuccessorError(
            f"confirmed row count {confirmed_count} != {EXPECTED_CONFIRMED_ROWS}"
        )
    if page_count != EXPECTED_AFFECTED_RAW_PAGES:
        raise PassingSectionSuccessorError(
            f"affected page count {page_count} != {EXPECTED_AFFECTED_RAW_PAGES}"
        )
    confirmed_ids = {
        str(identity) for identity in census["confirmed_row_identities"] if identity
    }
    unresolved_ids = {
        str(item["row_identity"])
        for item in census["unresolved_identities"]
        if item.get("row_identity")
    }
    successor_rows = [
        succeed_row(row, confirmed_ids=confirmed_ids, unresolved_ids=unresolved_ids)
        for row in census["rows"]
    ]
    changed = [
        row
        for row in successor_rows
        if row["attribution_state"] == "CONFIRMED_PASSING_SECTION_CORRECTION"
    ]
    team_confirmed = sum(
        row["player_identity_role"] == "TEAM_ATTRIBUTED_EVIDENCE" for row in changed
    )
    header_only = sum(1 for row in successor_rows if row.get("header_only"))
    join = active_path_join_audit(repo_root)
    return {
        "census": {
            key: value
            for key, value in census.items()
            if key not in {"rows", "confirmed_rows"}
        },
        "successor_rows": successor_rows,
        "impact": {
            "predecessor_rows": len(census["rows"]),
            "successor_rows": len(successor_rows),
            "changed_stat_group_rows": len(changed),
            "unchanged_rows": sum(
                1 for row in successor_rows if row["attribution_state"] == "UNCHANGED"
            ),
            "unresolved_rows": sum(
                1
                for row in successor_rows
                if row["attribution_state"] == "UNRESOLVED_AMBIGUOUS_SECTION"
            ),
            "confirmed_team_attributed_rows": team_confirmed,
            "header_only_rows": header_only,
            "counts_by_season": census["counts_by_season"],
            "predecessor_rewritten": False,
            "national_forecast_consumption_proven": False,
            "join_audit": join,
        },
    }


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    built = build_successor(data_root=data_root, repo_root=repo_root)
    payload_bytes = jsonl_bytes(built["successor_rows"])
    impact_bytes = (
        json.dumps(built["impact"], sort_keys=True, indent=2).encode("utf-8") + b"\n"
    )
    dataset_seed = {
        "contract_id": CONTRACT_ID,
        "predecessor_sha256": PREDECESSOR_PLAYER_SHA256,
        "successor_sha256": sha256_bytes(payload_bytes),
        "confirmed_rows": EXPECTED_CONFIRMED_ROWS,
    }
    dataset_identity = sha256_bytes(
        json.dumps(dataset_seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    payload_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / dataset_identity
    payload_root.mkdir(parents=True, exist_ok=True)
    player_name = "individual_player_statistics_successor.jsonl"
    impact_name = "old_to_new_impact.json"
    (payload_root / player_name).write_bytes(payload_bytes)
    (payload_root / impact_name).write_bytes(impact_bytes)
    predecessor_after = sha256_file(data_root / PREDECESSOR_PLAYER_RELATIVE)
    if predecessor_after != PREDECESSOR_PLAYER_SHA256:
        raise PassingSectionSuccessorError("predecessor mutated during materialize")
    gate = {
        "artifact_type": "TAMU_OFFICIAL_PASSING_SECTION_SUCCESSOR_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": PASS_RESULT,
        "dataset_identity": dataset_identity,
        "predecessor_payloads_rewritten": False,
        "publication_label": SHADOW_CLASSIFICATION,
        "census": {
            "confirmed_mislabeled_passing_rows": EXPECTED_CONFIRMED_ROWS,
            "confirmed_affected_raw_pages": EXPECTED_AFFECTED_RAW_PAGES,
            "screened_nonpassing_triple_rows": built["census"][
                "screened_nonpassing_triple_rows"
            ],
            "unresolved_section_matches": built["census"]["unresolved_section_matches"],
            "counts_by_season": built["census"]["counts_by_season"],
            "team_pseudo_player_rows": built["census"]["team_pseudo_player_rows"],
        },
        "impact": built["impact"],
        "predecessor": {
            "relative_path": PREDECESSOR_PLAYER_RELATIVE,
            "sha256": PREDECESSOR_PLAYER_SHA256,
            "rewritten": False,
        },
        "payloads": {
            "player_successor": {
                "relative_path": (
                    f"canonical/{PAYLOAD_SLUG}/sha256/{dataset_identity}/{player_name}"
                ),
                "sha256": sha256_bytes(payload_bytes),
                "bytes": len(payload_bytes),
                "row_count": len(built["successor_rows"]),
            },
            "impact": {
                "relative_path": (
                    f"canonical/{PAYLOAD_SLUG}/sha256/{dataset_identity}/{impact_name}"
                ),
                "sha256": sha256_bytes(impact_bytes),
                "bytes": len(impact_bytes),
            },
        },
        "scientific_nonclaims": [
            "Does not rewrite the 1996-2009 predecessor player corpus.",
            "Does not fabricate person identities for TEAM rows.",
            "Does not treat header-only tables as material statistic availability.",
            "Does not prove national-forecast consumption of the player corpus.",
            "Does not open the all-cycle trust gate or operator hold.",
        ],
    }
    gate["gate_identity"] = sha256_bytes(
        json.dumps(
            {key: value for key, value in gate.items() if key != "gate_identity"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return gate
