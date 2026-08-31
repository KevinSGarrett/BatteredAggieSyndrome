from __future__ import annotations

import hashlib
import html
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    canonical_json_bytes,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)

# Cycle #24 current-authority enrichment for the 2026 Week 1 universe.
#
# Four authority surfaces are bound here, and none of them rewrites a
# predecessor artifact:
#
#   A  the eight unsupported source participants are either resolved through an
#      official organization history page that links the exact season team
#      identifier the official schedule already carries, or they retain an
#      explicit abstention with the exact missing evidence;
#   B  the Associated Press Top 25 surface is completed by binding the poll
#      alias "Southern Cal" to the official team slug that carries the same
#      rank on a second official surface, after which every poll-eligible FBS
#      participant carries either a rank or an explicit unranked state and
#      every FCS participant carries a separate not-applicable state;
#   C  the official absolute kickoff instant is compared with the predecessor
#      schedule bound, so kickoff confirmation is earned rather than assumed;
#   D  venue identity is bound only where an institution publishes it for its
#      own home contest, and coordinates stay candidate-only, which keeps
#      weather out of admitted model input.

SCHEMA_VERSION = "aggie.shadow.week1_2026_authority_enrichment.v1"
CONTRACT_ID = "CYCLE24-WEEK1-2026-AUTHORITY-ENRICHMENT-V1"
JIRA_KEY = "BAT-683"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-AUTHORITY-ENRICHMENT-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "WEEK1_2026_CURRENT_AUTHORITY_ENRICHMENT"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_CURRENT_AUTHORITY_ENRICHMENT"

CONTRACT_RELATIVE = "configs/week1_2026_authority_enrichment_contract.json"
GATE_RELATIVE = "artifacts/authority/week1_2026_authority_enrichment_gate.json"
PAYLOAD_SLUG = "week1_2026_authority_enrichment"

KICKOFF_PAYLOAD_NAME = "week1_2026_kickoff_authority_rows.jsonl"
ENTITY_PAYLOAD_NAME = "week1_2026_entity_authority_rows.jsonl"
RANKING_PAYLOAD_NAME = "week1_2026_ranking_authority_rows.jsonl"
VENUE_PAYLOAD_NAME = "week1_2026_venue_authority_rows.jsonl"

INDEPENDENTLY_CONFIRMED = "INDEPENDENTLY_CONFIRMED"
KICKOFF_DISAGREES = "OFFICIAL_INSTANT_DISAGREES_WITH_PREDECESSOR_BOUND"
KICKOFF_ABSENT = "OFFICIAL_INSTANT_ABSENT"

RANKED_TOP_25 = "RANKED_TOP_25"
FBS_POLL_ELIGIBLE_UNRANKED = "FBS_POLL_ELIGIBLE_UNRANKED"
NOT_APPLICABLE_FBS_POLL = "NOT_APPLICABLE_FBS_POLL"
POLL_ROW_UNBOUND = "POLL_ROW_UNBOUND"

RESOLVED_AUTHORITATIVE_IDENTITY = "RESOLVED_AUTHORITATIVE_IDENTITY"
ABSTAIN_UNSUPPORTED_ENTITY = "ABSTAIN_UNSUPPORTED_ENTITY"

VENUE_IDENTITY_BOUND = "AUTHORITATIVE_VENUE_IDENTITY_BOUND"
VENUE_EVIDENCE_ABSENT = "SOURCE_EVIDENCE_ABSENT"
COORDINATES_CANDIDATE_ONLY = "CANDIDATE_ONLY"
WEATHER_CANDIDATE_ONLY = "CANDIDATE_ONLY_NOT_CONSUMED"

GATE_IDENTITY_FIELDS = (
    "artifact_type",
    "authority",
    "bound_predecessors",
    "classification",
    "contract_id",
    "contract_sha256",
    "coverage",
    "dataset_identity",
    "decision_unit",
    "entity_resolution",
    "focus_contest_report",
    "jira_key",
    "kickoff_authority",
    "lane",
    "local_issue_id",
    "manifest",
    "parent_jira_key",
    "payloads",
    "protected_lane",
    "ranking_completion",
    "record_hashes",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "season",
    "summary",
    "tamu_policy",
    "venue_and_weather",
    "week_label",
)


class AuthorityEnrichmentViolation(ValueError):
    """Raised when an authority-enrichment invariant is violated."""


# ---------------------------------------------------------------------------
# io helpers
# ---------------------------------------------------------------------------


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [field for field in GATE_IDENTITY_FIELDS if field not in gate]
    if missing:
        raise AuthorityEnrichmentViolation(
            f"gate is missing identity fields: {missing}"
        )
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    return load_contract_mapping(read_json(repo_root / CONTRACT_RELATIVE))


def load_contract_mapping(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a contract mapping so a relaxed policy can never be honoured."""
    contract = dict(contract)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityEnrichmentViolation(
            "authority enrichment contract identity drift"
        )
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise AuthorityEnrichmentViolation("authority enrichment schema drift")
    if contract.get("lane") != LANE:
        raise AuthorityEnrichmentViolation("authority enrichment lane drift")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityEnrichmentViolation("protected lane must remain blocked")
    if contract.get("jira_key") != JIRA_KEY:
        raise AuthorityEnrichmentViolation("authority enrichment owner drift")
    rules = contract["identity_rules"]
    for key in (
        "require_official_organization_identifier",
        "require_season_team_identifier_link",
        "require_exact_rank_agreement_for_alias_binding",
    ):
        if rules.get(key) is not True:
            raise AuthorityEnrichmentViolation(
                f"identity rule must remain enforced: {key}"
            )
    for key in (
        "forbid_display_name_only_resolution",
        "forbid_fuzzy_threshold_reduction",
    ):
        if rules.get(key) is not True:
            raise AuthorityEnrichmentViolation(
                f"identity guard must remain enforced: {key}"
            )
    weather = contract["weather_policy"]
    if not weather.get("admitted_requires_authoritative_venue_identity"):
        raise AuthorityEnrichmentViolation(
            "weather must require authoritative venue identity"
        )
    if not weather.get("admitted_requires_authoritative_coordinates"):
        raise AuthorityEnrichmentViolation(
            "weather must require authoritative coordinates"
        )
    if weather.get("observed_postgame_weather_forbidden") is not True:
        raise AuthorityEnrichmentViolation(
            "observed postgame weather must stay forbidden"
        )
    forbidden = contract["forbidden_ranking_encodings"]
    if forbidden.get("unranked_as_rank_26") is not False:
        raise AuthorityEnrichmentViolation("unranked must never be encoded as rank 26")
    if forbidden.get("fcs_as_ordinary_unranked_fbs") is not False:
        raise AuthorityEnrichmentViolation(
            "an FCS participant is not an unranked FBS participant"
        )
    if (
        contract["predecessor_immutability"].get("rewrites_predecessor_artifacts")
        is not False
    ):
        raise AuthorityEnrichmentViolation(
            "predecessor artifacts must not be rewritten"
        )
    if sorted(contract["protected_evidence"]["excluded_protected_seasons"]) != [
        2024,
        2025,
    ]:
        raise AuthorityEnrichmentViolation("protected seasons must remain excluded")
    return contract


def _payload_rows(
    data_root: Path, gate: Mapping[str, Any], name: str
) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise AuthorityEnrichmentViolation(f"predecessor payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


def _capture_manifest(data_root: Path, source: Mapping[str, Any]) -> dict[str, Any]:
    path = data_root / source["manifest_relative_path"]
    if not path.is_file():
        raise AuthorityEnrichmentViolation(
            f"missing capture manifest: {source['manifest_relative_path']}"
        )
    manifest = read_json(path)
    if manifest.get("capture_identity") != source["capture_identity"]:
        raise AuthorityEnrichmentViolation("capture manifest identity drift")
    return manifest


def _capture_text(
    data_root: Path, capture: Mapping[str, Any], expected_sha: str | None = None
) -> str:
    relative = capture.get("raw_relative_path")
    if not relative:
        raise AuthorityEnrichmentViolation("capture has no raw payload")
    path = data_root / relative
    digest = sha256_file(path)
    if digest != capture["raw_sha256"]:
        raise AuthorityEnrichmentViolation("raw capture hash drift")
    if expected_sha is not None and digest != expected_sha:
        raise AuthorityEnrichmentViolation("raw capture is not the pinned capture")
    return path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# source parsing
# ---------------------------------------------------------------------------


def normalize_name_key(value: str) -> str:
    text = html.unescape(value or "").strip().lower()
    text = text.replace(".", " ").replace("'", "").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_contest_graph(text: str, *, graph_key: str) -> list[dict[str, Any]]:
    """Extract the embedded official contest graph from a scoreboard capture."""
    marker = f'"{graph_key}":['
    start = text.find(marker)
    if start < 0:
        raise AuthorityEnrichmentViolation(
            "official contest graph is absent from the capture"
        )
    fragment = text[start + len(marker) - 1 :]
    depth = 0
    for index, char in enumerate(fragment):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return json.loads(fragment[: index + 1])
    raise AuthorityEnrichmentViolation("official contest graph is truncated")


def index_contest_graph(
    games: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Key the official contest graph by the declared cross-source identity tuple."""
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for game in games:
        teams = game.get("teams") or []
        if len(teams) != 2:
            continue
        home = next((team for team in teams if team.get("isHome")), None)
        away = next((team for team in teams if not team.get("isHome")), None)
        if home is None or away is None:
            continue
        month, day, year = game["startDate"].split("/")
        key = (
            f"{year}-{month}-{day}",
            normalize_name_key(home.get("nameShort", "")),
            normalize_name_key(away.get("nameShort", "")),
        )
        if key in index:
            raise AuthorityEnrichmentViolation(
                f"official contest graph is ambiguous for {key}"
            )
        index[key] = {"contest": game, "home": home, "away": away}
    return index


def parse_poll_rows(text: str) -> list[dict[str, Any]]:
    """Extract the ordered poll table from an official rankings capture."""
    rows: list[dict[str, Any]] = []
    for match in re.finditer(r"<tr>(.*?)</tr>", text, re.S):
        cells = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cell)).strip()
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", match.group(1), re.S)
        ]
        if len(cells) < 2:
            continue
        rank_cell = cells[0]
        tie = rank_cell.startswith("T")
        digits = rank_cell[1:] if tie else rank_cell
        if not digits.isdigit():
            continue
        rows.append(
            {
                "rank": int(digits),
                "tie_group": rank_cell if tie else None,
                "poll_display_name": html.unescape(cells[1]).strip(),
                "poll_display_name_key": normalize_name_key(cells[1]),
                "points": cells[2] if len(cells) > 2 else None,
            }
        )
    return rows


def parse_official_season_membership(
    text: str, *, source_team_id: str
) -> dict[str, Any] | None:
    """Read the season row that links the exact season team identifier."""
    pattern = re.compile(
        r"<tr[^>]*>\s*<td[^>]*><a href=\"/teams/"
        + re.escape(source_team_id)
        + r"\">(?P<season>[^<]+)</a></td>(?P<rest>.*?)</tr>",
        re.S,
    )
    match = pattern.search(text)
    if match is None:
        return None
    cells = [
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cell)).strip()
        for cell in re.findall(r"<td[^>]*>(.*?)</td>", match.group("rest"), re.S)
    ]
    if len(cells) < 3:
        return None
    return {
        "official_season_label": match.group("season").strip(),
        "head_coach_evidence_present": bool(cells[0]),
        "subdivision": cells[1].strip(),
        "conference_label": cells[2].strip(),
    }


def parse_institutional_venue(text: str, *, opponent_key: str) -> dict[str, Any] | None:
    """Read the venue an institution publishes for its own named home contest."""
    for match in re.finditer(
        r"schedule-event-item__teams(.{0,6000}?)schedule-event-item__loc", text, re.S
    ):
        block = match.group(1)
        names = [
            normalize_name_key(re.sub(r"<[^>]+>", " ", name))
            for name in re.findall(
                r"schedule-event-default__name[^>]*>(.*?)</strong>", block, re.S
            )
        ]
        if opponent_key not in names:
            continue
        venue = re.search(
            r"schedule-event-default__venue[^>]*>(.*?)</span>", block, re.S
        )
        city = re.search(
            r"schedule-event-default__stadium[^>]*>(.*?)</span>", block, re.S
        )
        if venue is None:
            return None
        return {
            "venue_identity": html.unescape(
                re.sub(r"<[^>]+>|<!--\[-->|<!--\]-->", "", venue.group(1))
            ).strip(),
            "venue_city": html.unescape(
                re.sub(
                    r"<[^>]+>|<!--\[-->|<!--\]-->", "", city.group(1) if city else ""
                )
            ).strip()
            or None,
            "published_team_names": names,
        }
    return None


# ---------------------------------------------------------------------------
# input loading
# ---------------------------------------------------------------------------


def load_inputs(repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    sources = contract["sources"]

    gates: dict[str, dict[str, Any]] = {}
    for name in ("spine_semantic_successor", "schedule_identity"):
        source = sources[name]
        path = repo_root / source["gate_relative_path"]
        if not path.is_file():
            raise AuthorityEnrichmentViolation(
                f"missing predecessor gate: {source['gate_relative_path']}"
            )
        gate = read_json(path)
        if gate.get("gate_identity") != source["gate_identity"]:
            raise AuthorityEnrichmentViolation(
                f"predecessor gate identity drift for {name}"
            )
        gates[name] = gate

    schedule_gate = gates["schedule_identity"]
    contests = _payload_rows(
        data_root, schedule_gate, sources["schedule_identity"]["contest_payload_name"]
    )
    participants = _payload_rows(
        data_root,
        schedule_gate,
        sources["schedule_identity"]["participant_payload_name"],
    )
    spine_rows = _payload_rows(
        data_root,
        gates["spine_semantic_successor"],
        sources["spine_semantic_successor"]["row_payload_name"],
    )

    kickoff_source = sources["kickoff_authority_capture"]
    kickoff_manifest = _capture_manifest(data_root, kickoff_source)
    kickoff_capture = next(
        item for item in kickoff_manifest["captures"] if item.get("state") == "CAPTURED"
    )
    kickoff_text = _capture_text(
        data_root, kickoff_capture, kickoff_source["raw_sha256"]
    )

    entity_source = sources["entity_authority_capture"]
    entity_manifest = _capture_manifest(data_root, entity_source)
    if int(entity_manifest.get("captured_count", 0)) != int(
        entity_source["expected_capture_count"]
    ):
        raise AuthorityEnrichmentViolation("entity authority capture count drift")

    venue_source = sources["venue_authority_capture"]
    venue_manifest = _capture_manifest(data_root, venue_source)
    venue_capture = next(
        item for item in venue_manifest["captures"] if item.get("state") == "CAPTURED"
    )
    venue_text = _capture_text(data_root, venue_capture, venue_source["raw_sha256"])

    ranking_source = sources["ranking_capture"]
    ranking_manifest = _capture_manifest(data_root, ranking_source)
    ranking_capture = next(
        item for item in ranking_manifest["captures"] if item.get("state") == "CAPTURED"
    )
    ranking_text = _capture_text(
        data_root, ranking_capture, ranking_source["raw_sha256"]
    )

    return {
        "contract": contract,
        "gates": gates,
        "contests": contests,
        "participants": participants,
        "spine_rows": spine_rows,
        "kickoff_manifest": kickoff_manifest,
        "kickoff_capture": kickoff_capture,
        "kickoff_text": kickoff_text,
        "entity_manifest": entity_manifest,
        "venue_manifest": venue_manifest,
        "venue_capture": venue_capture,
        "venue_text": venue_text,
        "ranking_manifest": ranking_manifest,
        "ranking_capture": ranking_capture,
        "ranking_text": ranking_text,
    }


# ---------------------------------------------------------------------------
# surface construction
# ---------------------------------------------------------------------------


def _contest_key(contest: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        contest["requested_game_date"],
        normalize_name_key(contest["home_team"]["source_display_name"]),
        normalize_name_key(contest["away_team"]["source_display_name"]),
    )


def build_kickoff_rows(
    *,
    contests: Sequence[Mapping[str, Any]],
    spine_rows: Sequence[Mapping[str, Any]],
    kickoff_text: str,
    kickoff_capture: Mapping[str, Any],
    graph_key: str,
) -> list[dict[str, Any]]:
    """Compare each official absolute kickoff instant with the predecessor bound."""
    graph = index_contest_graph(parse_contest_graph(kickoff_text, graph_key=graph_key))
    bounds = {
        row["contest_identity"]: row["kickoff_utc_conservative_lower_bound"]
        for row in spine_rows
    }
    rows: list[dict[str, Any]] = []
    for contest in contests:
        key = _contest_key(contest)
        matched = graph.get(key)
        predecessor_bound = bounds.get(contest["contest_identity"])
        row: dict[str, Any] = {
            "contest_identity": contest["contest_identity"],
            "ncaa_contest_id": contest["ncaa_contest_id"],
            "requested_game_date": contest["requested_game_date"],
            "home_normalized_name_key": key[1],
            "away_normalized_name_key": key[2],
            "predecessor_kickoff_bound_utc": predecessor_bound,
            "official_contest_id": None,
            "official_kickoff_epoch": None,
            "official_kickoff_utc": None,
            "official_local_start_time": None,
            "official_start_date": None,
            "broadcaster_name": None,
            "kickoff_confirmation_state": KICKOFF_ABSENT,
            "kickoff_utc_independently_confirmed": False,
            "cross_source_identity_tuple_matched": matched is not None,
            "source_id": "SRC-NCAA-OFFICIAL-COM",
            "raw_capture_sha256": kickoff_capture["raw_sha256"],
            "retrieved_at_utc": kickoff_capture["retrieved_at_utc"],
        }
        if matched is not None:
            contest_graph = matched["contest"]
            epoch = contest_graph.get("startTimeEpoch")
            official_utc = (
                datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                if epoch and contest_graph.get("hasStartTime")
                else None
            )
            row.update(
                {
                    "official_contest_id": str(contest_graph.get("contestId")),
                    "official_kickoff_epoch": int(epoch) if epoch else None,
                    "official_kickoff_utc": official_utc,
                    "official_local_start_time": contest_graph.get("startTime") or None,
                    "official_start_date": contest_graph.get("startDate"),
                    "broadcaster_name": contest_graph.get("broadcasterName") or None,
                }
            )
            if official_utc is None:
                row["kickoff_confirmation_state"] = KICKOFF_ABSENT
            elif predecessor_bound is not None and official_utc == predecessor_bound:
                row["kickoff_confirmation_state"] = INDEPENDENTLY_CONFIRMED
                row["kickoff_utc_independently_confirmed"] = True
            else:
                row["kickoff_confirmation_state"] = KICKOFF_DISAGREES
        row["row_identity"] = stable_hash(row)
        rows.append(row)
    return sorted(rows, key=lambda item: item["contest_identity"])


def build_entity_rows(
    *,
    contract: Mapping[str, Any],
    data_root: Path,
    entity_manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Resolve or truthfully retain each unsupported source participant."""
    captures = {
        int(item["official_organization_id"]): item
        for item in entity_manifest["captures"]
    }
    rows: list[dict[str, Any]] = []
    for declared in contract["unresolved_participants"]:
        org_id = int(declared["official_organization_id"])
        capture = captures.get(org_id)
        row: dict[str, Any] = {
            "source_display_name": declared["source_display_name"],
            "source_team_id": declared["source_team_id"],
            "official_organization_id": org_id,
            "official_organization_uri": None,
            "official_season_label": None,
            "official_subdivision": None,
            "official_conference_label": None,
            "season_team_identifier_link_observed": False,
            "resolved_by_display_name_only": False,
            "authoritative_identity": None,
            "canonical_development_history_available": False,
            "disposition": ABSTAIN_UNSUPPORTED_ENTITY,
            "missing_evidence": ["OFFICIAL_ORGANIZATION_HISTORY_CAPTURE_ABSENT"],
            "source_id": "SRC-NCAA-OFFICIAL-STATS",
            "raw_capture_sha256": None,
            "retrieved_at_utc": None,
        }
        if capture is not None and capture.get("state") == "CAPTURED":
            text = _capture_text(data_root, capture)
            membership = parse_official_season_membership(
                text, source_team_id=declared["source_team_id"]
            )
            row.update(
                {
                    "official_organization_uri": capture["source_uri"],
                    "raw_capture_sha256": capture["raw_sha256"],
                    "retrieved_at_utc": capture["retrieved_at_utc"],
                }
            )
            if membership is None:
                row["missing_evidence"] = [
                    "OFFICIAL_ORGANIZATION_HISTORY_DOES_NOT_LINK_THE_DECLARED_SEASON_TEAM_IDENTIFIER"
                ]
            else:
                row.update(
                    {
                        "official_season_label": membership["official_season_label"],
                        "official_subdivision": membership["subdivision"],
                        "official_conference_label": membership["conference_label"],
                        "season_team_identifier_link_observed": True,
                        "authoritative_identity": f"SRC-NCAA-OFFICIAL-STATS:ORG:{org_id}",
                        "disposition": RESOLVED_AUTHORITATIVE_IDENTITY,
                        "missing_evidence": [],
                    }
                )
        row["row_identity"] = stable_hash(row)
        rows.append(row)
    return sorted(rows, key=lambda item: item["source_team_id"])


def build_ranking_rows(
    *,
    contract: Mapping[str, Any],
    participants: Sequence[Mapping[str, Any]],
    ranking_text: str,
    ranking_capture: Mapping[str, Any],
    kickoff_text: str,
    graph_key: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Complete the poll surface, binding aliases only through rank agreement."""
    poll_rows = parse_poll_rows(ranking_text)
    expected = int(contract["sources"]["ranking_capture"]["expected_ranked_row_count"])
    if len(poll_rows) != expected:
        raise AuthorityEnrichmentViolation(
            f"official poll row count drift: {len(poll_rows)} != {expected}"
        )

    official_ranks: dict[str, int] = {}
    official_rank_by_name_key: dict[str, dict[str, Any]] = {}
    for game in parse_contest_graph(kickoff_text, graph_key=graph_key):
        for team in game.get("teams") or []:
            rank = team.get("teamRank")
            if not rank:
                continue
            official_ranks[team["seoname"]] = int(rank)
            official_rank_by_name_key[normalize_name_key(team.get("nameShort", ""))] = {
                "rank": int(rank),
                "official_team_slug": team["seoname"],
            }

    declared_rank_values = {item["rank"] for item in poll_rows}
    unsupported = {
        key: value
        for key, value in official_rank_by_name_key.items()
        if value["rank"] not in declared_rank_values
    }
    if unsupported:
        raise AuthorityEnrichmentViolation(
            f"official slug ranks disagree with the poll table: {sorted(unsupported)}"
        )

    alias_records: list[dict[str, Any]] = []
    alias_by_poll_key: dict[str, dict[str, Any]] = {}
    for alias in contract["ranking_alias_bindings"]:
        slug = alias["official_team_slug"]
        observed = official_ranks.get(slug)
        poll_row = next(
            (
                item
                for item in poll_rows
                if normalize_name_key(item["poll_display_name"])
                == normalize_name_key(alias["poll_display_name"])
            ),
            None,
        )
        record = {
            "poll_display_name": alias["poll_display_name"],
            "official_team_slug": slug,
            "canonical_team_id": alias["canonical_team_id"],
            "normalized_name_key": alias["normalized_name_key"],
            "declared_rank": int(alias["declared_rank"]),
            "poll_rank_observed": poll_row["rank"] if poll_row else None,
            "poll_tie_group_observed": poll_row["tie_group"] if poll_row else None,
            "official_slug_rank_observed": observed,
            "binding_rule": alias["binding_rule"],
            "resolved_by_display_name_only": False,
            "binding_state": "ALIAS_UNBOUND_INSUFFICIENT_AUTHORITY",
        }
        if (
            poll_row is not None
            and observed is not None
            and poll_row["rank"] == observed == int(alias["declared_rank"])
        ):
            record["binding_state"] = "ALIAS_BOUND_THROUGH_RANK_AGREEMENT"
            alias_by_poll_key[normalize_name_key(alias["poll_display_name"])] = alias
        record["record_identity"] = stable_hash(record)
        alias_records.append(record)

    # The poll table is the rank authority; the official contest graph is the
    # identity authority, because it publishes the same rank against an official
    # team slug and the exact short name the official schedule already carries.
    poll_by_name_key: dict[str, dict[str, Any]] = {}
    for item in poll_rows:
        key = item["poll_display_name_key"]
        alias = alias_by_poll_key.get(key)
        if alias is not None:
            key = normalize_name_key(alias["normalized_name_key"])
            item = dict(item, bound_through_alias=True)
        else:
            item = dict(item, bound_through_alias=False)
        poll_by_name_key[key] = item
    for key, official in official_rank_by_name_key.items():
        poll_row = next(
            (item for item in poll_rows if item["rank"] == official["rank"]), None
        )
        if poll_row is None:
            continue
        poll_by_name_key.setdefault(
            key,
            dict(
                poll_row,
                bound_through_alias=False,
                official_team_slug=official["official_team_slug"],
            ),
        )

    rows: list[dict[str, Any]] = []
    for participant in participants:
        subdivision = participant.get("subdivision")
        names = [
            normalize_name_key(name)
            for name in participant.get("source_display_names", [])
        ]
        matched_key = next((key for key in names if key in poll_by_name_key), None)
        poll_row = poll_by_name_key.get(matched_key) if matched_key else None
        if subdivision != "FBS":
            state = NOT_APPLICABLE_FBS_POLL
            rank: int | None = None
            is_unranked = False
        elif poll_row is not None:
            state = RANKED_TOP_25
            rank = int(poll_row["rank"])
            is_unranked = False
        else:
            state = FBS_POLL_ELIGIBLE_UNRANKED
            rank = None
            is_unranked = True
        row = {
            "participant_identity": participant["participant_identity"],
            "canonical_team_id": participant.get("canonical_team_id"),
            "source_team_id": participant.get("source_team_id"),
            "source_display_names": participant.get("source_display_names", []),
            "subdivision": subdivision,
            "poll_id": contract["sources"]["ranking_capture"]["poll_id"],
            "ranking_state": state,
            "poll_rank": rank,
            "is_unranked": is_unranked,
            "tie_group": poll_row["tie_group"] if poll_row else None,
            "bound_through_alias": bool(
                poll_row and poll_row.get("bound_through_alias")
            ),
            "raw_capture_sha256": ranking_capture["raw_sha256"],
            "retrieved_at_utc": ranking_capture["retrieved_at_utc"],
        }
        row["row_identity"] = stable_hash(row)
        rows.append(row)

    bound_rank_values = {
        row["poll_rank"] for row in rows if row["poll_rank"] is not None
    }
    observed_in_universe = set(official_ranks.values())
    unbound = sorted(observed_in_universe - bound_rank_values)
    outside_universe = sorted(declared_rank_values - bound_rank_values)
    for record in alias_records:
        record["unbound_poll_ranks_after_binding"] = unbound
        record["poll_ranks_absent_from_the_week1_universe"] = outside_universe
    return sorted(rows, key=lambda item: item["participant_identity"]), alias_records


def build_venue_rows(
    *,
    contract: Mapping[str, Any],
    contests: Sequence[Mapping[str, Any]],
    spine_rows: Sequence[Mapping[str, Any]],
    venue_text: str,
    venue_capture: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Bind venue identity only where an institution publishes its own home venue."""
    venue_source = contract["sources"]["venue_authority_capture"]
    licensed_home = normalize_name_key(
        venue_source["licensed_home_normalized_name_key"]
    )
    published_opponent_keys = {
        normalize_name_key(item["away_normalized_name_key"]): normalize_name_key(
            item["institutional_published_name_key"]
        )
        for item in venue_source.get("licensed_contests", [])
    }
    coordinate_states = {
        row["contest_identity"]: row.get("venue_coordinate_state") for row in spine_rows
    }
    rows: list[dict[str, Any]] = []
    for contest in contests:
        key = _contest_key(contest)
        licensed = key[1] == licensed_home and key[2] in published_opponent_keys
        published = (
            parse_institutional_venue(
                venue_text, opponent_key=published_opponent_keys[key[2]]
            )
            if licensed
            else None
        )
        row: dict[str, Any] = {
            "contest_identity": contest["contest_identity"],
            "ncaa_contest_id": contest["ncaa_contest_id"],
            "requested_game_date": contest["requested_game_date"],
            "home_normalized_name_key": key[1],
            "away_normalized_name_key": key[2],
            "venue_authority_licensed_for_this_contest": licensed,
            "venue_identity": None,
            "venue_city": None,
            "venue_identity_state": VENUE_EVIDENCE_ABSENT,
            "venue_identity_admitted_from_site_orientation_alone": False,
            "venue_coordinate_state": coordinate_states.get(contest["contest_identity"])
            or COORDINATES_CANDIDATE_ONLY,
            "venue_coordinates_admitted": False,
            "weather_state": WEATHER_CANDIDATE_ONLY,
            "weather_admitted_model_input": False,
            "source_id": "SRC-TAMU-OFFICIAL-ATHLETICS" if licensed else None,
            "raw_capture_sha256": venue_capture["raw_sha256"] if licensed else None,
            "retrieved_at_utc": venue_capture["retrieved_at_utc"] if licensed else None,
        }
        if published is not None and published["venue_identity"]:
            row.update(
                {
                    "venue_identity": published["venue_identity"],
                    "venue_city": published["venue_city"],
                    "venue_identity_state": VENUE_IDENTITY_BOUND,
                }
            )
        row["row_identity"] = stable_hash(row)
        rows.append(row)
    return sorted(rows, key=lambda item: item["contest_identity"])


# ---------------------------------------------------------------------------
# gate construction
# ---------------------------------------------------------------------------


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def build_expected(
    *,
    repo_root: Path,
    data_root: Path,
    inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconstruct every authority surface from pinned captures alone."""
    resolved = dict(inputs if inputs is not None else load_inputs(repo_root, data_root))
    contract = resolved["contract"]
    graph_key = contract["sources"]["kickoff_authority_capture"]["embedded_graph_key"]

    kickoff_rows = build_kickoff_rows(
        contests=resolved["contests"],
        spine_rows=resolved["spine_rows"],
        kickoff_text=resolved["kickoff_text"],
        kickoff_capture=resolved["kickoff_capture"],
        graph_key=graph_key,
    )
    entity_rows = build_entity_rows(
        contract=contract,
        data_root=data_root,
        entity_manifest=resolved["entity_manifest"],
    )
    ranking_rows, alias_records = build_ranking_rows(
        contract=contract,
        participants=resolved["participants"],
        ranking_text=resolved["ranking_text"],
        ranking_capture=resolved["ranking_capture"],
        kickoff_text=resolved["kickoff_text"],
        graph_key=graph_key,
    )
    venue_rows = build_venue_rows(
        contract=contract,
        contests=resolved["contests"],
        spine_rows=resolved["spine_rows"],
        venue_text=resolved["venue_text"],
        venue_capture=resolved["venue_capture"],
    )

    focus = contract["focus_contest"]
    focus_key = (
        focus["requested_game_date"],
        normalize_name_key(focus["home_normalized_name_key"]),
        normalize_name_key(focus["away_normalized_name_key"]),
    )
    focus_kickoff = next(
        (
            row
            for row in kickoff_rows
            if (
                row["requested_game_date"],
                row["home_normalized_name_key"],
                row["away_normalized_name_key"],
            )
            == focus_key
        ),
        None,
    )
    focus_venue = next(
        (
            row
            for row in venue_rows
            if (
                row["requested_game_date"],
                row["home_normalized_name_key"],
                row["away_normalized_name_key"],
            )
            == focus_key
        ),
        None,
    )
    if focus_kickoff is None or focus_venue is None:
        raise AuthorityEnrichmentViolation(
            "the focus contest is absent from the official schedule"
        )

    focus_report = {
        "requested_game_date": focus["requested_game_date"],
        "ncaa_contest_id": focus_kickoff["ncaa_contest_id"],
        "contest_identity": focus_kickoff["contest_identity"],
        "official_contest_id": focus_kickoff["official_contest_id"],
        "official_kickoff_utc": focus_kickoff["official_kickoff_utc"],
        "official_kickoff_epoch": focus_kickoff["official_kickoff_epoch"],
        "official_local_start_time": focus_kickoff["official_local_start_time"],
        "expected_kickoff_utc": focus["expected_kickoff_utc"],
        "expected_local_kickoff": focus["expected_local_kickoff"],
        "kickoff_confirmation_state": focus_kickoff["kickoff_confirmation_state"],
        "kickoff_matches_declared_calendar": focus_kickoff["official_kickoff_utc"]
        == focus["expected_kickoff_utc"],
        "broadcaster_name": focus_kickoff["broadcaster_name"],
        "venue_identity": focus_venue["venue_identity"],
        "venue_city": focus_venue["venue_city"],
        "venue_identity_state": focus_venue["venue_identity_state"],
        "venue_identity_matches_declared_venue": focus_venue["venue_identity"]
        == focus["expected_venue_identity"],
        "venue_coordinate_state": focus_venue["venue_coordinate_state"],
        "weather_state": focus_venue["weather_state"],
        "kickoff_raw_capture_sha256": focus_kickoff["raw_capture_sha256"],
        "kickoff_retrieved_at_utc": focus_kickoff["retrieved_at_utc"],
        "venue_raw_capture_sha256": focus_venue["raw_capture_sha256"],
        "venue_retrieved_at_utc": focus_venue["retrieved_at_utc"],
        "custom_correction_applied": False,
        "tamu_specific_adjustment_applied": False,
    }

    record_hashes = {
        "kickoff_rows": stable_hash(kickoff_rows),
        "entity_rows": stable_hash(entity_rows),
        "ranking_rows": stable_hash(ranking_rows),
        "venue_rows": stable_hash(venue_rows),
        "alias_records": stable_hash(alias_records),
    }
    contract_sha256 = hashlib.sha256(
        (repo_root / CONTRACT_RELATIVE).read_bytes()
    ).hexdigest()
    code_identity = sha256_file(Path(__file__).resolve())
    dataset_identity = stable_hash(
        {
            "classification": CLASSIFICATION,
            "code_identity": code_identity,
            "contract_sha256": contract_sha256,
            "predecessor_spine_successor_gate_identity": resolved["gates"][
                "spine_semantic_successor"
            ]["gate_identity"],
            "predecessor_schedule_gate_identity": resolved["gates"][
                "schedule_identity"
            ]["gate_identity"],
            "record_hashes": record_hashes,
        }
    )

    ranked = [row for row in ranking_rows if row["ranking_state"] == RANKED_TOP_25]
    kickoff_summary = {
        "confirmation_state_counts": _counts(
            row["kickoff_confirmation_state"] for row in kickoff_rows
        ),
        "independently_confirmed_count": sum(
            1 for row in kickoff_rows if row["kickoff_utc_independently_confirmed"]
        ),
        "cross_source_matched_count": sum(
            1 for row in kickoff_rows if row["cross_source_identity_tuple_matched"]
        ),
        "official_instant_present_count": sum(
            1 for row in kickoff_rows if row["official_kickoff_utc"] is not None
        ),
        "contest_count": len(kickoff_rows),
    }
    entity_summary = {
        "disposition_counts": _counts(row["disposition"] for row in entity_rows),
        "resolved_by_display_name_only_count": sum(
            1 for row in entity_rows if row["resolved_by_display_name_only"]
        ),
        "fuzzy_threshold_reduced": False,
        "resolved": [
            {
                "source_display_name": row["source_display_name"],
                "source_team_id": row["source_team_id"],
                "official_organization_id": row["official_organization_id"],
                "authoritative_identity": row["authoritative_identity"],
                "official_subdivision": row["official_subdivision"],
                "official_conference_label": row["official_conference_label"],
                "official_season_label": row["official_season_label"],
            }
            for row in entity_rows
            if row["disposition"] == RESOLVED_AUTHORITATIVE_IDENTITY
        ],
        "retained_abstentions": [
            {
                "source_display_name": row["source_display_name"],
                "source_team_id": row["source_team_id"],
                "missing_evidence": row["missing_evidence"],
            }
            for row in entity_rows
            if row["disposition"] == ABSTAIN_UNSUPPORTED_ENTITY
        ],
        "canonical_development_history_available_count": sum(
            1 for row in entity_rows if row["canonical_development_history_available"]
        ),
    }
    ranking_summary = {
        "poll_id": contract["sources"]["ranking_capture"]["poll_id"],
        "state_counts": _counts(row["ranking_state"] for row in ranking_rows),
        "ranked_participant_count": len(ranked),
        "distinct_bound_ranks": sorted({row["poll_rank"] for row in ranked}),
        "alias_bindings": alias_records,
        "unranked_encoded_as_26_count": sum(
            1 for row in ranking_rows if row["poll_rank"] == 26
        ),
        "fcs_participants_marked_not_applicable": sum(
            1 for row in ranking_rows if row["ranking_state"] == NOT_APPLICABLE_FBS_POLL
        ),
        "unbound_poll_ranks": sorted(
            {
                rank
                for record in alias_records
                for rank in record["unbound_poll_ranks_after_binding"]
            }
        ),
        "poll_ranks_absent_from_the_week1_universe": sorted(
            {
                rank
                for record in alias_records
                for rank in record["poll_ranks_absent_from_the_week1_universe"]
            }
        ),
        "poll_surface_complete": all(
            record["binding_state"] == "ALIAS_BOUND_THROUGH_RANK_AGREEMENT"
            for record in alias_records
        )
        and not any(
            record["unbound_poll_ranks_after_binding"] for record in alias_records
        ),
    }
    venue_summary = {
        "venue_identity_state_counts": _counts(
            row["venue_identity_state"] for row in venue_rows
        ),
        "venue_coordinate_state_counts": _counts(
            row["venue_coordinate_state"] for row in venue_rows
        ),
        "weather_state_counts": _counts(row["weather_state"] for row in venue_rows),
        "authoritative_venue_identity_count": sum(
            1
            for row in venue_rows
            if row["venue_identity_state"] == VENUE_IDENTITY_BOUND
        ),
        "authoritative_coordinate_count": sum(
            1 for row in venue_rows if row["venue_coordinates_admitted"]
        ),
        "weather_admitted_model_input_count": sum(
            1 for row in venue_rows if row["weather_admitted_model_input"]
        ),
        "venue_identity_admitted_from_site_orientation_alone_count": sum(
            1
            for row in venue_rows
            if row["venue_identity_admitted_from_site_orientation_alone"]
        ),
    }
    summary = {
        "contest_count": len(kickoff_rows),
        "participant_count": len(ranking_rows),
        "unresolved_participant_row_count": len(entity_rows),
        "resolved_participant_count": len(entity_summary["resolved"]),
        "retained_abstention_count": len(entity_summary["retained_abstentions"]),
        "independently_confirmed_kickoff_count": kickoff_summary[
            "independently_confirmed_count"
        ],
        "authoritative_venue_identity_count": venue_summary[
            "authoritative_venue_identity_count"
        ],
        "poll_surface_complete": ranking_summary["poll_surface_complete"],
        "weather_admitted_model_input": bool(
            venue_summary["weather_admitted_model_input_count"]
        ),
        "forecast_emitted": False,
        "prior_materialized": False,
    }

    return {
        "contract": contract,
        "contract_sha256": contract_sha256,
        "code_identity": code_identity,
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "kickoff_rows": kickoff_rows,
        "entity_rows": entity_rows,
        "ranking_rows": ranking_rows,
        "venue_rows": venue_rows,
        "alias_records": alias_records,
        "kickoff_authority": kickoff_summary,
        "entity_resolution": entity_summary,
        "ranking_completion": ranking_summary,
        "venue_and_weather": venue_summary,
        "focus_contest_report": focus_report,
        "summary": summary,
        "gates": resolved["gates"],
    }


PAYLOAD_ROLES = (
    (KICKOFF_PAYLOAD_NAME, "WEEK1_2026_KICKOFF_AUTHORITY_ROWS", "kickoff_rows"),
    (ENTITY_PAYLOAD_NAME, "WEEK1_2026_ENTITY_AUTHORITY_ROWS", "entity_rows"),
    (RANKING_PAYLOAD_NAME, "WEEK1_2026_RANKING_AUTHORITY_ROWS", "ranking_rows"),
    (VENUE_PAYLOAD_NAME, "WEEK1_2026_VENUE_AUTHORITY_ROWS", "venue_rows"),
)


def enforce_invariants(gate: Mapping[str, Any]) -> None:
    """Fail closed on every authority invariant this decision unit owns."""
    if gate["protected_lane"] != PROTECTED_LANE:
        raise AuthorityEnrichmentViolation("protected lane must remain blocked")
    if gate["lane"] != LANE:
        raise AuthorityEnrichmentViolation("authority enrichment lane drift")
    if (
        gate["bound_predecessors"]["predecessor_artifacts_rewritten_in_place"]
        is not False
    ):
        raise AuthorityEnrichmentViolation(
            "predecessor artifacts must not be rewritten"
        )
    for key in ("t_minus_24h_state", "t_minus_90m_state"):
        if gate["checkpoints"].get(key) != "OPEN":
            raise AuthorityEnrichmentViolation(f"{key} is no longer OPEN")
    for key in ("executed_early", "pregame_result_access", "week1_outcome_access"):
        if gate["checkpoints"].get(key) is not False:
            raise AuthorityEnrichmentViolation(f"forbidden checkpoint behaviour: {key}")
    if gate["summary"]["forecast_emitted"] is not False:
        raise AuthorityEnrichmentViolation("this gate must not emit a forecast")
    if gate["summary"]["prior_materialized"] is not False:
        raise AuthorityEnrichmentViolation(
            "this gate must not materialize a strength prior"
        )

    venue = gate["venue_and_weather"]
    if venue["weather_admitted_model_input_count"]:
        raise AuthorityEnrichmentViolation(
            "weather must not become admitted model input"
        )
    if venue["authoritative_coordinate_count"]:
        raise AuthorityEnrichmentViolation(
            "no 2026 venue-coordinate authority is declared, so coordinates cannot be admitted"
        )
    if venue["venue_identity_admitted_from_site_orientation_alone_count"]:
        raise AuthorityEnrichmentViolation(
            "venue identity must never be admitted from site orientation alone"
        )

    ranking = gate["ranking_completion"]
    if ranking["unranked_encoded_as_26_count"]:
        raise AuthorityEnrichmentViolation("unranked must never be encoded as rank 26")
    if ranking["state_counts"].get(POLL_ROW_UNBOUND):
        raise AuthorityEnrichmentViolation("a poll row remains unbound")
    if not ranking["fcs_participants_marked_not_applicable"]:
        raise AuthorityEnrichmentViolation(
            "FCS participants must carry a separate not-applicable poll state"
        )

    entity = gate["entity_resolution"]
    if entity["resolved_by_display_name_only_count"]:
        raise AuthorityEnrichmentViolation(
            "an entity was resolved by display name alone"
        )
    if entity["fuzzy_threshold_reduced"] is not False:
        raise AuthorityEnrichmentViolation("the fuzzy threshold must not be reduced")
    if entity["canonical_development_history_available_count"]:
        raise AuthorityEnrichmentViolation(
            "a newly resolved organization must not claim canonical development history"
        )

    focus = gate["focus_contest_report"]
    if focus["custom_correction_applied"] or focus["tamu_specific_adjustment_applied"]:
        raise AuthorityEnrichmentViolation(
            "no focus-contest specific adjustment is permitted"
        )

    for key in ("custom_correction_applied", "tamu_specific_adjustment_applied"):
        if gate["tamu_policy"].get(key) is not False:
            raise AuthorityEnrichmentViolation(
                f"an A&M-specific adjustment is declared: {key}"
            )


def build_gate(
    *,
    expected: Mapping[str, Any],
    manifest_entry: Mapping[str, Any],
    payloads: Sequence[Mapping[str, Any]],
    execution_time_utc: str,
) -> dict[str, Any]:
    contract = expected["contract"]
    sources = contract["sources"]
    gate: dict[str, Any] = {
        "artifact_type": "WEEK1_2026_AUTHORITY_ENRICHMENT_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": contract["decision_unit"],
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "season": contract["season"],
        "week_label": contract["week_label"],
        "result": PASS_RESULT,
        "issued_at_utc": execution_time_utc,
        "dataset_identity": expected["dataset_identity"],
        "manifest": dict(manifest_entry),
        "payloads": [dict(item) for item in payloads],
        "record_hashes": expected["record_hashes"],
        "authority": {
            "policy": contract["authority"],
            "kickoff": {
                "source_id": "SRC-NCAA-OFFICIAL-COM",
                "capture_identity": sources["kickoff_authority_capture"][
                    "capture_identity"
                ],
                "raw_sha256": sources["kickoff_authority_capture"]["raw_sha256"],
                "source_uri": sources["kickoff_authority_capture"]["source_uri"],
            },
            "entity": {
                "source_id": "SRC-NCAA-OFFICIAL-STATS",
                "capture_identity": sources["entity_authority_capture"][
                    "capture_identity"
                ],
            },
            "ranking": {
                "source_id": "SRC-NCAA-OFFICIAL-COM",
                "capture_identity": sources["ranking_capture"]["capture_identity"],
                "raw_sha256": sources["ranking_capture"]["raw_sha256"],
                "poll_id": sources["ranking_capture"]["poll_id"],
            },
            "venue": {
                "source_id": "SRC-TAMU-OFFICIAL-ATHLETICS",
                "capture_identity": sources["venue_authority_capture"][
                    "capture_identity"
                ],
                "raw_sha256": sources["venue_authority_capture"]["raw_sha256"],
                "source_uri": sources["venue_authority_capture"]["source_uri"],
            },
        },
        "bound_predecessors": {
            "spine_semantic_successor_gate_identity": sources[
                "spine_semantic_successor"
            ]["gate_identity"],
            "schedule_identity_gate_identity": sources["schedule_identity"][
                "gate_identity"
            ],
            "bound_predecessor_gate_identities": contract["predecessor_immutability"][
                "bound_predecessor_gate_identities"
            ],
            "predecessor_artifacts_rewritten_in_place": False,
        },
        "coverage": {
            "contest_count": expected["summary"]["contest_count"],
            "participant_count": expected["summary"]["participant_count"],
            "venue_row_count": len(expected["venue_rows"]),
            "unresolved_participant_row_count": expected["summary"][
                "unresolved_participant_row_count"
            ],
        },
        "kickoff_authority": expected["kickoff_authority"],
        "entity_resolution": expected["entity_resolution"],
        "ranking_completion": expected["ranking_completion"],
        "venue_and_weather": expected["venue_and_weather"],
        "focus_contest_report": expected["focus_contest_report"],
        "summary": expected["summary"],
        "checkpoints": contract["checkpoints"],
        "tamu_policy": contract["tamu_policy"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    enforce_invariants(gate)
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    return gate


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    execution_time: datetime,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = dict(
        expected
        if expected is not None
        else build_expected(repo_root=repo_root, data_root=data_root)
    )
    execution_time_utc = (
        execution_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if execution_time.microsecond
        else execution_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    identity = resolved["dataset_identity"]
    canonical_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / identity
    manifest_root = data_root / "manifests" / PAYLOAD_SLUG / "sha256" / identity

    payloads: list[dict[str, Any]] = []
    for name, role, key in PAYLOAD_ROLES:
        rows = resolved[key]
        payload_bytes = jsonl_bytes(rows)
        path = canonical_root / name
        _write_bytes(path, payload_bytes)
        payloads.append(
            {
                "name": name,
                "role": role,
                "relative_path": _relative(path, data_root),
                "rows": len(rows),
                "bytes": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_AUTHORITY_ENRICHMENT_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": resolved["contract"]["decision_unit"],
        "local_issue_id": LOCAL_ISSUE_ID,
        "dataset_identity": identity,
        "issued_at_utc": execution_time_utc,
        "classification": CLASSIFICATION,
        "record_hashes": resolved["record_hashes"],
        "summary": resolved["summary"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": resolved["code_identity"],
            "contract_sha256": resolved["contract_sha256"],
        },
    }
    manifest_path = manifest_root / f"{PAYLOAD_SLUG}_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")

    manifest_entry = {
        "relative_path": _relative(manifest_path, data_root),
        "dataset_identity": identity,
        "authoritative_sha256": manifest_authoritative_sha256(manifest),
    }
    gate = build_gate(
        expected=resolved,
        manifest_entry=manifest_entry,
        payloads=[
            {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")}
            for item in payloads
        ],
        execution_time_utc=execution_time_utc,
    )
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"gate": gate, "manifest": manifest, "expected": resolved}


def _compare(path: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            errors.append(f"{path}: expected object")
            return
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                errors.append(f"{path}.{key}: unexpected key")
            elif key not in actual:
                errors.append(f"{path}.{key}: missing key")
            else:
                _compare(f"{path}.{key}", actual[key], expected[key], errors)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: list shape mismatch")
            return
        for index, (left, right) in enumerate(zip(actual, expected)):
            _compare(f"{path}[{index}]", left, right, errors)
        return
    if actual != expected:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    """Independently reconstruct the authority surfaces and refuse any regression."""
    gate = read_json(repo_root / GATE_RELATIVE)
    if gate.get("result") != PASS_RESULT:
        raise AuthorityEnrichmentViolation(
            f"authority gate is not passing: {gate.get('result')}"
        )
    enforce_invariants(gate)
    if compute_gate_identity(gate) != gate.get("gate_identity"):
        raise AuthorityEnrichmentViolation(
            "gate identity does not match its identity-bearing fields"
        )
    if binding_identity(gate, "binding_identity") != gate.get("binding_identity"):
        raise AuthorityEnrichmentViolation("cross-surface binding identity drift")
    if not require_rebuild:
        return {
            "result": "PASS",
            "mode": "SCHEMA_ONLY",
            "gate_identity": gate["gate_identity"],
        }

    expected = build_expected(repo_root=repo_root, data_root=data_root)
    errors: list[str] = []
    if gate["dataset_identity"] != expected["dataset_identity"]:
        errors.append("dataset identity drift")
    _compare("record_hashes", gate["record_hashes"], expected["record_hashes"], errors)
    _compare("summary", gate["summary"], expected["summary"], errors)
    _compare(
        "kickoff_authority",
        gate["kickoff_authority"],
        expected["kickoff_authority"],
        errors,
    )
    _compare(
        "entity_resolution",
        gate["entity_resolution"],
        expected["entity_resolution"],
        errors,
    )
    _compare(
        "ranking_completion",
        gate["ranking_completion"],
        expected["ranking_completion"],
        errors,
    )
    _compare(
        "venue_and_weather",
        gate["venue_and_weather"],
        expected["venue_and_weather"],
        errors,
    )
    _compare(
        "focus_contest_report",
        gate["focus_contest_report"],
        expected["focus_contest_report"],
        errors,
    )

    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    if (
        manifest_authoritative_sha256(manifest)
        != gate["manifest"]["authoritative_sha256"]
    ):
        errors.append("manifest authoritative content drift")
    for payload in gate["payloads"]:
        entry = next(
            (item for item in manifest["payloads"] if item["name"] == payload["name"]),
            None,
        )
        if entry is None:
            errors.append(f"payload missing from manifest: {payload['name']}")
            continue
        for key in ("rows", "bytes", "sha256", "role"):
            if entry[key] != payload[key]:
                errors.append(f"payload {payload['name']} {key} drift")
        path = data_root / entry["relative_path"]
        if not path.is_file():
            errors.append(f"payload absent on disk: {entry['relative_path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"payload rehash drift: {entry['relative_path']}")

    for row in expected["venue_rows"]:
        if (
            row["venue_identity_state"] == VENUE_IDENTITY_BOUND
            and not row["venue_identity"]
        ):
            errors.append("venue identity bound without an authoritative venue name")
        if row["venue_coordinates_admitted"]:
            errors.append(
                "venue coordinates admitted without a declared coordinate authority"
            )
        if row["weather_admitted_model_input"]:
            errors.append("weather admitted as model input")
    for row in expected["ranking_rows"]:
        if row["poll_rank"] == 26:
            errors.append("unranked encoded as rank 26")
        if (
            row["subdivision"] != "FBS"
            and row["ranking_state"] != NOT_APPLICABLE_FBS_POLL
        ):
            errors.append(
                "an FCS participant was represented as an ordinary unranked FBS team"
            )
        if row["ranking_state"] == RANKED_TOP_25 and not (
            1 <= int(row["poll_rank"]) <= 25
        ):
            errors.append("a bound rank falls outside the Top 25")
    for row in expected["entity_rows"]:
        if (
            row["disposition"] == RESOLVED_AUTHORITATIVE_IDENTITY
            and not row["season_team_identifier_link_observed"]
        ):
            errors.append(
                "an entity was resolved without a season team identifier link"
            )
        if (
            row["disposition"] == ABSTAIN_UNSUPPORTED_ENTITY
            and not row["missing_evidence"]
        ):
            errors.append("an abstention omitted its exact missing evidence")
    for row in expected["kickoff_rows"]:
        if row["kickoff_utc_independently_confirmed"] and (
            row["official_kickoff_utc"] != row["predecessor_kickoff_bound_utc"]
        ):
            errors.append("kickoff confirmation claimed without instant agreement")

    if errors:
        raise AuthorityEnrichmentViolation(
            "independent authority validation failed: " + "; ".join(errors[:16])
        )
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
        "summary": gate["summary"],
        "focus_contest_report": gate["focus_contest_report"],
    }
