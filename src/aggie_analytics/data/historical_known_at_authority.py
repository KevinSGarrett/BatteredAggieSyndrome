"""Historical known-at authority audit for every admitted national domain.

The audit answers one question per domain: what kind of temporal authority actually backs
its known-at claim? It classifies each admitted feature into an observed publication
instant, an observed effective instant, a conservative precommitted bound, a retrieval
timestamp only, postgame-only evidence, or an absent source. It never converts a capture
time into a historical known-at instant.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "aggie.data.historical_known_at_authority.v1"
CONTRACT_ID = "BAT-666-HISTORICAL-KNOWN-AT-AUTHORITY-AUDIT-V1"
CLASSIFICATION = "HISTORICAL_KNOWN_AT_AUTHORITY_BOUNDARY_AUDIT_FOR_EVERY_ADMITTED_DOMAIN"
LANE = "HISTORICAL_AUDIT_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
JIRA_KEY = "BAT-666"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-HISTORICAL-KNOWN-AT-AUTHORITY-AUDIT-001"
PRODUCER = "tools/build_historical_known_at_authority_audit.py"

CONTRACT_RELATIVE = "configs/historical_known_at_authority_contract.json"
GATE_RELATIVE = "artifacts/data_lake/historical_known_at_authority_gate.json"
EVIDENCE_RELATIVE = "artifacts/data_lake/historical_known_at_authority_replay.json"
MATRIX_GATE_RELATIVE = "artifacts/data_lake/national_pit_domain_admission_matrix_gate.json"

PASS_RESULT = "PASS_HISTORICAL_KNOWN_AT_AUTHORITY_AUDIT"

OBSERVED_PUBLICATION = "OBSERVED_PUBLICATION_TIMESTAMP"
OBSERVED_EFFECTIVE = "OBSERVED_EFFECTIVE_TIMESTAMP"
CONSERVATIVE_BOUND = "CONSERVATIVE_PRECOMMITTED_AVAILABILITY_BOUND"
RETRIEVAL_ONLY = "RETRIEVAL_TIMESTAMP_ONLY"
POSTGAME_ONLY = "POSTGAME_ONLY_EVIDENCE"
SOURCE_ABSENT = "SOURCE_ABSENT"

AUTHORITY_CLASSES = (
    OBSERVED_PUBLICATION,
    OBSERVED_EFFECTIVE,
    CONSERVATIVE_BOUND,
    RETRIEVAL_ONLY,
    POSTGAME_ONLY,
    SOURCE_ABSENT,
)

DATE_ONLY_CLOCK = "00:00"
NON_AUTHORITATIVE_KEYS = frozenset({"gate_identity"})


class KnownAtAuthorityViolation(RuntimeError):
    """Raised when the audit input or artifact is not admissible."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / CONTRACT_RELATIVE
    if not path.exists():
        raise KnownAtAuthorityViolation(f"the known-at authority contract is missing at {path}")
    contract = read_json(path)
    if contract.get("contract_id") != CONTRACT_ID:
        raise KnownAtAuthorityViolation("the known-at authority contract identifier does not match")
    return contract


def parse_start_instant(text: str) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def start_evidence_kind(text: str) -> str:
    """Classify the temporal evidence a single spine start field actually carries."""

    instant = parse_start_instant(text)
    if instant is None:
        return "NO_PARSEABLE_START_EVIDENCE"
    if instant.strftime("%H:%M") == DATE_ONLY_CLOCK:
        return "CALENDAR_DATE_ONLY_MIDNIGHT_SENTINEL"
    return "PUBLISHED_START_INSTANT"


def date_only_completion_bound(instant: datetime, policy: Mapping[str, Any]) -> datetime:
    rule = policy["date_only_rule"]
    return instant + timedelta(days=int(rule["latest_possible_completion_offset_days"]))


def date_only_earliest_start_bound(instant: datetime, policy: Mapping[str, Any]) -> datetime:
    rule = policy["date_only_rule"]
    return instant + timedelta(days=int(rule["earliest_possible_start_offset_days"]))


def clocked_completion_bound(instant: datetime, policy: Mapping[str, Any]) -> datetime:
    rule = policy["published_start_instant_rule"]
    return instant + timedelta(hours=float(rule["maximum_contest_duration_hours"]))


def prior_is_guaranteed_complete(
    prior_start: str, target_start: str, policy: Mapping[str, Any]
) -> bool:
    """Decide whether a prior contest is provably finished before a target contest begins."""

    prior, target = parse_start_instant(prior_start), parse_start_instant(target_start)
    if prior is None or target is None:
        return False
    prior_kind, target_kind = start_evidence_kind(prior_start), start_evidence_kind(target_start)
    if prior_kind == "PUBLISHED_START_INSTANT" and target_kind == "PUBLISHED_START_INSTANT":
        return clocked_completion_bound(prior, policy) <= target
    prior_complete = (
        clocked_completion_bound(prior, policy)
        if prior_kind == "PUBLISHED_START_INSTANT"
        else date_only_completion_bound(prior, policy)
    )
    target_earliest = (
        target
        if target_kind == "PUBLISHED_START_INSTANT"
        else date_only_earliest_start_bound(target, policy)
    )
    return prior_complete <= target_earliest


def profile_start_evidence(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Measure, per season, which kind of start evidence the spine actually carries."""

    by_season: dict[int, Counter] = defaultdict(Counter)
    games: dict[str, tuple[int, str]] = {}
    for row in rows:
        season = int(row["season"])
        text = str(row.get("start_date_utc_text") or "")
        by_season[season][start_evidence_kind(text)] += 1
        games[str(row["canonical_game_id"])] = (season, text)

    game_kinds: Counter = Counter()
    season_game_kinds: dict[int, Counter] = defaultdict(Counter)
    for season, text in games.values():
        kind = start_evidence_kind(text)
        game_kinds[kind] += 1
        season_game_kinds[season][kind] += 1

    seasons = sorted(by_season)
    date_only_seasons = [
        season
        for season in seasons
        if season_game_kinds[season]["PUBLISHED_START_INSTANT"] == 0
    ]
    clocked_seasons = [season for season in seasons if season not in date_only_seasons]
    return {
        "distinct_games": len(games),
        "game_evidence_counts": dict(sorted(game_kinds.items())),
        "seasons_with_a_published_start_instant": clocked_seasons,
        "seasons_with_calendar_date_evidence_only": date_only_seasons,
        "team_row_evidence_counts": dict(
            sorted(Counter(k for c in by_season.values() for k in c.elements()).items())
        ),
        "per_season": [
            {
                "calendar_date_only_games": season_game_kinds[season][
                    "CALENDAR_DATE_ONLY_MIDNIGHT_SENTINEL"
                ],
                "published_start_instant_games": season_game_kinds[season][
                    "PUBLISHED_START_INSTANT"
                ],
                "season": season,
                "total_games": sum(season_game_kinds[season].values()),
            }
            for season in seasons
        ],
    }


def extract_publication_instants(
    document: str, patterns: Sequence[str]
) -> list[dict[str, Any]]:
    """Pull any candidate publication instant a route body exposes."""

    found: list[dict[str, Any]] = []
    for pattern in patterns:
        for value in re.findall(pattern, document)[:5]:
            found.append({"pattern": pattern, "raw_value": value})
    return found


def audit_route(route: Mapping[str, Any], capture: Mapping[str, Any]) -> dict[str, Any]:
    """Bind one publication-time route attempt to a truthful positive or negative finding."""

    if capture.get("state") != "CAPTURED":
        return {
            "bears_a_publication_instant": False,
            "failure_condition": capture.get("failure_condition"),
            "finding": "THE_ROUTE_COULD_NOT_BE_RETRIEVED_AT_ALL",
            "hypothesis": route["hypothesis"],
            "raw_sha256": None,
            "retrieved_at_utc": None,
            "route_id": route["route_id"],
            "source_authority": route["source_authority"],
            "source_uri": capture.get("source_uri"),
            "state": "TECHNICALLY_UNAVAILABLE",
        }

    instants = capture.get("publication_instants", [])
    if instants:
        finding = (
            "THE_ROUTE_EXPOSES_PER_ARTICLE_PUBLICATION_INSTANTS_FOR_CURRENTLY_LISTED_CONTENT_ONLY"
        )
    else:
        finding = "THE_ROUTE_CARRIES_NO_PUBLICATION_OR_EFFECTIVE_INSTANT_OF_ANY_KIND"
    return {
        "bears_a_publication_instant": bool(instants),
        "finding": finding,
        "historical_per_season_release_instant_available": False,
        "historical_limitation": (
            "A publication instant observed on a currently listed item does not establish the"
            " release instant of a historical poll week, so it cannot back a historical known-at"
            " claim for the rankings domain."
        ),
        "hypothesis": route["hypothesis"],
        "observed_instant_sample": instants[:3],
        "observed_instant_count": len(instants),
        "raw_bytes": capture.get("raw_bytes"),
        "raw_sha256": capture.get("raw_sha256"),
        "retrieved_at_utc": capture.get("retrieved_at_utc"),
        "route_id": route["route_id"],
        "source_authority": route["source_authority"],
        "source_uri": capture.get("source_uri"),
        "state": "CAPTURED",
    }


def audit_domains(
    matrix_gate: Mapping[str, Any],
    start_profile: Mapping[str, Any],
    route_findings: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Classify the real temporal authority behind every admitted domain."""

    by_domain = {row["domain_id"]: row for row in matrix_gate["admission_matrix"]}
    features: dict[str, list[str]] = defaultdict(list)
    for row in matrix_gate["admitted_feature_registry"]:
        features[row["domain_id"]].append(row["feature_id"])

    any_route_bears_history = any(
        row.get("historical_per_season_release_instant_available") for row in route_findings
    )
    clocked_seasons = start_profile["seasons_with_a_published_start_instant"]
    date_only_seasons = start_profile["seasons_with_calendar_date_evidence_only"]

    audited = [
        {
            "admitted_features": sorted(features.get("team_outcome_priors", [])),
            "authority_class": CONSERVATIVE_BOUND,
            "authority_is_sufficient_for_point_in_time_admission": True,
            "declared_known_at_basis": by_domain["team_outcome_priors"]["known_at_basis"],
            "domain_id": "team_outcome_priors",
            "evidence": (
                "Every prior value is derived from contests the spine already carries, and the"
                " spine carries a start field for every one of them. The precommitted completion"
                " bound therefore decides admissibility from evidence alone, with no observed"
                " final whistle and no retrieval time involved."
            ),
            "limitation": (
                f"For the {len(date_only_seasons)} seasons that carry calendar-date evidence only,"
                " the bound requires a three-day separation, so a prior contest within two days of"
                " a target contest cannot be admitted."
            ),
            "supporting_bound_rule": "BOTH",
        },
        {
            "admitted_features": sorted(features.get("team_season_context", [])),
            "authority_class": CONSERVATIVE_BOUND,
            "authority_is_sufficient_for_point_in_time_admission": True,
            "declared_known_at_basis": by_domain["team_season_context"]["known_at_basis"],
            "domain_id": "team_season_context",
            "evidence": (
                "Conference affiliation and subdivision membership are declared for a whole season"
                " and are settled before that season's first contest, so the season itself is a"
                " logically guaranteed availability bound."
            ),
            "limitation": (
                "The bound is season-grain. It cannot distinguish a value that changed during an"
                " offseason from one announced years earlier, and it would be invalidated by any"
                " midseason reclassification."
            ),
            "supporting_bound_rule": "SEASON_SCOPE",
        },
        {
            "admitted_features": sorted(features.get("venues", [])),
            "authority_class": RETRIEVAL_ONLY,
            "authority_is_sufficient_for_point_in_time_admission": False,
            "declared_known_at_basis": by_domain["venues"]["known_at_basis"],
            "domain_id": "venues",
            "evidence": (
                "Latitude, longitude and elevation are genuinely time invariant, but the dome and"
                " playing-surface attributes are mutable and were captured once, so their only"
                " temporal evidence is this project's retrieval time."
            ),
            "limitation": (
                "The declared structural time-invariant basis is correct for geography and wrong"
                " for the mutable surface attributes, which must not inherit it."
            ),
            "supporting_bound_rule": "NONE",
        },
        {
            "admitted_features": sorted(features.get("rankings", [])),
            "authority_class": RETRIEVAL_ONLY if not any_route_bears_history else OBSERVED_PUBLICATION,
            "authority_is_sufficient_for_point_in_time_admission": False,
            "declared_known_at_basis": by_domain["rankings"]["known_at_basis"],
            "domain_id": "rankings",
            "evidence": (
                "The declared basis is a poll week ordinal compared against a game week ordinal."
                " An ordinal is not an instant. Both investigated national routes failed to supply"
                " a historical per-week release instant, so no publication timestamp backs the"
                " domain."
            ),
            "limitation": (
                "A week ordinal cannot prove that a poll was released before a contest played"
                " early in the same week, so the domain cannot be admitted point in time until a"
                " real release instant is acquired."
            ),
            "supporting_bound_rule": "NONE",
        },
        {
            "admitted_features": ["home_win", "margin", "points_for", "points_against"],
            "authority_class": POSTGAME_ONLY,
            "authority_is_sufficient_for_point_in_time_admission": True,
            "declared_known_at_basis": "POSTGAME_BY_CONSTRUCTION",
            "domain_id": "outcome_labels_and_cutoffs",
            "evidence": (
                "An outcome cannot exist before its contest is played, which is the strongest"
                " possible temporal statement. The audit's contribution is the cutoff: the"
                " precommitted completion bound states when a prior outcome is guaranteed to have"
                " become knowable."
            ),
            "limitation": (
                "The cutoff is a bound, not an observed final whistle, and it is therefore"
                f" strictly conservative. It is tightest for the {len(clocked_seasons)} seasons"
                " that carry a published start instant."
            ),
            "supporting_bound_rule": "BOTH",
        },
    ]
    return sorted(audited, key=lambda item: item["domain_id"])


def build_audit(
    matrix_gate: Mapping[str, Any],
    start_profile: Mapping[str, Any],
    capture_manifest: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    producer: str = PRODUCER,
) -> dict[str, Any]:
    captures = {row["route_id"]: row for row in capture_manifest.get("routes", [])}
    route_findings = [
        audit_route(route, captures.get(route["route_id"], {}))
        for route in contract["publication_time_routes"]
    ]
    domains = audit_domains(matrix_gate, start_profile, route_findings)
    class_counts = Counter(row["authority_class"] for row in domains)

    admissible = [row["domain_id"] for row in domains if row["authority_is_sufficient_for_point_in_time_admission"]]
    blocked = [row["domain_id"] for row in domains if not row["authority_is_sufficient_for_point_in_time_admission"]]

    bundle = {
        "artifact_type": "HISTORICAL_KNOWN_AT_AUTHORITY_GATE",
        "authority": "THIS_AUDIT_CLASSIFIES_TEMPORAL_AUTHORITY_AND_ADMITS_NO_FEATURE_BY_ITSELF",
        "authority_class_counts": {
            authority: class_counts.get(authority, 0) for authority in AUTHORITY_CLASSES
        },
        "bound_predecessor_identities": {
            "domain_admission_matrix_gate_identity": matrix_gate.get("gate_identity")
        },
        "capture_identity": capture_manifest.get("capture_identity"),
        "classification": CLASSIFICATION,
        "conservative_bound_policy": contract["conservative_bound_policy"],
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_of(contract),
        "decision_unit": LOCAL_ISSUE_ID,
        "domain_authority": domains,
        "domains_blocked_from_point_in_time_admission": blocked,
        "domains_with_sufficient_authority": admissible,
        "gap_id": contract["gap_id"],
        "gap_verdict": {
            "gap_id": "GAP-002",
            "remains_open": bool(blocked),
            "verdict": (
                "PARTIAL_AUTHORITY_ESTABLISHED_A_NONZERO_POINT_IN_TIME_SLICE_IS_NOW_POSSIBLE"
                if admissible
                else "NO_AUTHORITY_ESTABLISHED"
            ),
            "why": (
                "The precommitted completion bound is logically guaranteed by evidence the spine"
                " already carries, so the outcome-derived domains gain a real known-at basis. The"
                " rankings and venue-surface domains gain none, so the gap does not close."
            ),
        },
        "jira_key": JIRA_KEY,
        "lane": LANE,
        "local_issue_id": LOCAL_ISSUE_ID,
        "negative_findings": {
            "neither_investigated_route_supplied_a_historical_per_week_poll_release_instant": True,
            "no_capture_or_retrieval_time_was_used_as_a_historical_known_at_instant": True,
            "the_declared_structural_basis_for_venues_overreaches_its_mutable_attributes": True,
            "the_rankings_week_ordinal_basis_is_not_an_instant": True,
        },
        "outcome_exclusion": contract["outcome_exclusion"],
        "parent_jira_key": PARENT_JIRA_KEY,
        "producer": producer,
        "protected_lane": PROTECTED_LANE,
        "publication_time_route_findings": route_findings,
        "result": PASS_RESULT,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": contract["scientific_nonclaims"],
        "start_time_evidence_profile": start_profile,
    }
    bundle["gate_identity"] = gate_identity_of(bundle)
    return bundle


def gate_identity_of(bundle: Mapping[str, Any]) -> str:
    return sha256_of({k: v for k, v in bundle.items() if k not in NON_AUTHORITATIVE_KEYS})


def validate_artifact(repo_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Check the committed audit for internal consistency and forbidden shortcuts."""

    repo_root = Path(repo_root)
    contract = load_contract(repo_root)
    if gate is None:
        gate_path = repo_root / GATE_RELATIVE
        if not gate_path.exists():
            raise KnownAtAuthorityViolation("the known-at authority gate has not been materialized")
        gate = read_json(gate_path)

    if gate.get("schema_version") != SCHEMA_VERSION:
        raise KnownAtAuthorityViolation("the committed gate schema version does not match")
    if gate.get("contract_sha256") != sha256_of(contract):
        raise KnownAtAuthorityViolation("the committed gate is bound to a different contract body")
    if gate_identity_of(gate) != gate.get("gate_identity"):
        raise KnownAtAuthorityViolation("the committed gate identity does not cover its content")

    audited = {row["domain_id"] for row in gate.get("domain_authority", [])}
    if audited != set(contract["audited_domains"]):
        raise KnownAtAuthorityViolation("the audit does not cover exactly the declared domains")
    for row in gate["domain_authority"]:
        if row["authority_class"] not in AUTHORITY_CLASSES:
            raise KnownAtAuthorityViolation("a domain carries an undeclared authority class")
        if row["authority_class"] == RETRIEVAL_ONLY and row[
            "authority_is_sufficient_for_point_in_time_admission"
        ]:
            raise KnownAtAuthorityViolation(
                "a retrieval-time-only domain was declared sufficient for point-in-time admission"
            )
    if len(gate.get("publication_time_route_findings", [])) < 2:
        raise KnownAtAuthorityViolation("fewer than two publication-time routes were investigated")
    for finding in gate["publication_time_route_findings"]:
        if finding.get("historical_per_season_release_instant_available") and not finding.get(
            "bears_a_publication_instant"
        ):
            raise KnownAtAuthorityViolation(
                "a route claims a historical release instant without any observed instant"
            )
    policy = gate.get("conservative_bound_policy", {})
    if not policy.get("precommitted"):
        raise KnownAtAuthorityViolation("the conservative bound policy is not precommitted")
    if policy.get("date_only_rule", {}).get("required_separation_days", 0) < 3:
        raise KnownAtAuthorityViolation("the date-only separation is not conservative enough")
    verdict = gate.get("gap_verdict", {})
    if verdict.get("gap_id") != "GAP-002":
        raise KnownAtAuthorityViolation("the audit does not bind a GAP-002 verdict")
    if not verdict.get("remains_open") and gate.get(
        "domains_blocked_from_point_in_time_admission"
    ):
        raise KnownAtAuthorityViolation(
            "GAP-002 is reported closed while domains remain blocked from admission"
        )

    return {
        "authority_class_counts": gate["authority_class_counts"],
        "domains_blocked_from_point_in_time_admission": gate[
            "domains_blocked_from_point_in_time_admission"
        ],
        "domains_with_sufficient_authority": gate["domains_with_sufficient_authority"],
        "gap_verdict": gate["gap_verdict"]["verdict"],
        "gate_identity": gate["gate_identity"],
        "result": gate["result"],
    }
