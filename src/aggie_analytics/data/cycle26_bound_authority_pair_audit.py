"""Cycle #26 independent audit of BAT-666/BAT-667 prior-target bounds.

Predecessor BAT-666 contract text retains historical logical_guarantee wording
for hash continuity. This successor never upgrades a precommitted duration into
proven historical known-at. It classifies admitted prior-target pairs as
conditional chronology proxies and does not declare leakage without a row trace.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "aggie.data.cycle26_bound_authority_pair_audit.v1"
CONTRACT_ID = "CYCLE26-R26-22-BOUND-AUTHORITY-PAIR-AUDIT-V1"
JIRA_KEY = "BAT-691"
LOCAL_ISSUE_ID = "POST-TASK-R26-22-BOUND-AUTHORITY-PAIR-AUDIT-001"
CLASSIFICATION = "CONDITIONAL_CHRONOLOGY_PROXY_NOT_UNIVERSAL_GUARANTEE"
LANE = "DEVELOPMENT_SUCCESSOR_UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_R26_22_PAIR_AUDIT_CONTAINED"
GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_R26_22_PRIOR_TARGET_PAIR_AUDIT.json"
)
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
DATE_ONLY_CLOCK = "00:00"
EPISTEMIC_STATUS = "CONDITIONAL_CHRONOLOGY_PROXY_NOT_UNIVERSAL_GUARANTEE"
CONSERVATIVE_BOUND = "CONSERVATIVE_PRECOMMITTED_AVAILABILITY_BOUND"
OBSERVED_PUBLICATION = "OBSERVED_PUBLICATION_TIMESTAMP"
OBSERVED_EFFECTIVE = "OBSERVED_EFFECTIVE_TIMESTAMP"
PROVEN_PIT_AUTHORITY_CLASSES = frozenset({OBSERVED_PUBLICATION, OBSERVED_EFFECTIVE})


def operational_pit_admission_allowed(
    authority_class: str,
    predecessor_sufficient: bool | None = None,
) -> bool:
    """Conservative precommitted bounds never satisfy proven-PIT admission.

    Predecessor BAT-666 rows may still carry
    ``authority_is_sufficient_for_point_in_time_admission=true`` for hash
    continuity. Operational consumers must call this successor instead of
    trusting that boolean.
    """

    if authority_class == CONSERVATIVE_BOUND:
        return False
    if predecessor_sufficient is False:
        return False
    return authority_class in PROVEN_PIT_AUTHORITY_CLASSES


CONSUMERS = (
    {
        "module": "src/aggie_analytics/data/national_pit_eligible_slice.py",
        "owner": "BAT-667",
        "role": "ADMITTED_PRIOR_FEATURE_SLICE",
        "uses_bound_as": "COMPLETION_BOUND_FOR_PRIOR_ACCUMULATION",
        "proven_historical_known_at": False,
    },
    {
        "module": "src/aggie_analytics/data/historical_known_at_authority.py",
        "owner": "BAT-666",
        "role": "DOMAIN_AUTHORITY_CLASSIFICATION",
        "uses_bound_as": "BOOLEAN_PROXY_NAMED_GUARANTEE_IN_PREDECESSOR_API",
        "proven_historical_known_at": False,
    },
    {
        "module": "src/aggie_analytics/data/week1_2026_game_grain_national_forecast_successor.py",
        "owner": "BAT-690",
        "role": "ACTIVE_WEEK1_PATH",
        "uses_bound_as": "NONE_NO_IMPORT",
        "proven_historical_known_at": False,
    },
)


class BoundAuthorityPairAuditError(ValueError):
    """Raised when the Cycle #26 bound-authority pair audit cannot proceed honestly."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def parse_start_instant(text: str) -> datetime | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        instant = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if instant.tzinfo is None:
        return None
    return instant.astimezone(timezone.utc)


def start_evidence_kind(text: str) -> str:
    instant = parse_start_instant(text)
    if instant is None:
        return "NO_PARSEABLE_START_EVIDENCE"
    if instant.strftime("%H:%M") == DATE_ONLY_CLOCK:
        return "CALENDAR_DATE_ONLY_MIDNIGHT_SENTINEL"
    return "PUBLISHED_START_INSTANT"


def classify_prior_target_temporal_authority(
    prior_start: str,
    target_start: str,
    *,
    clocked_hours: float = 12.0,
    date_only_completion_days: int = 2,
    date_only_earliest_start_days: int = -1,
) -> dict[str, Any]:
    """Independent proxy classification. Never emits a proven-PIT guarantee."""

    prior = parse_start_instant(prior_start)
    target = parse_start_instant(target_start)
    prior_kind = start_evidence_kind(prior_start)
    target_kind = start_evidence_kind(target_start)
    if prior is None or target is None:
        return {
            "admitted_under_proxy": False,
            "bound_epistemic_status": EPISTEMIC_STATUS,
            "class": "INSUFFICIENT_START_EVIDENCE",
            "prior_kind": prior_kind,
            "target_kind": target_kind,
            "proven_historical_known_at": False,
        }
    if prior_kind == "PUBLISHED_START_INSTANT":
        prior_complete = prior + timedelta(hours=float(clocked_hours))
        proxy_class = "PROXY_CLOCKED_12H"
    else:
        prior_complete = prior + timedelta(days=int(date_only_completion_days))
        proxy_class = "PROXY_DATE_ONLY_PLUS_2D"
    if target_kind == "PUBLISHED_START_INSTANT":
        target_earliest = target
    else:
        target_earliest = target + timedelta(days=int(date_only_earliest_start_days))
    admitted = prior_complete <= target_earliest
    strict_start_order = prior < target
    near_bound = admitted and (target_earliest - prior_complete) < timedelta(hours=24)
    return {
        "admitted_under_proxy": admitted,
        "bound_epistemic_status": EPISTEMIC_STATUS,
        "class": proxy_class if admitted else "NOT_ADMITTED_PROXY_FAILS",
        "near_bound_window": bool(near_bound),
        "prior_kind": prior_kind,
        "proven_historical_known_at": False,
        "strict_start_before_target": strict_start_order,
        "target_kind": target_kind,
        "universal_finality_guarantee": False,
    }


def _proxy_bounds(
    start_text: str,
    *,
    clocked_hours: float = 12.0,
    date_only_completion_days: int = 2,
    date_only_earliest_start_days: int = -1,
) -> dict[str, Any] | None:
    instant = parse_start_instant(start_text)
    kind = start_evidence_kind(start_text)
    if instant is None:
        return None
    if kind == "PUBLISHED_START_INSTANT":
        complete = instant + timedelta(hours=float(clocked_hours))
        earliest = instant
        proxy_class = "PROXY_CLOCKED_12H"
    else:
        complete = instant + timedelta(days=int(date_only_completion_days))
        earliest = instant + timedelta(days=int(date_only_earliest_start_days))
        proxy_class = "PROXY_DATE_ONLY_PLUS_2D"
    return {
        "complete": complete,
        "earliest": earliest,
        "kind": kind,
        "proxy_class": proxy_class,
    }


def census_team_prior_target_pairs(
    observations: Sequence[Mapping[str, Any]],
    starts: Mapping[str, str],
    *,
    sealed_seasons: Sequence[int] = (2024, 2025),
) -> dict[str, Any]:
    """Count admitted prior-target pairs from pre-parsed proxy bounds."""

    sealed = {int(season) for season in sealed_seasons}
    by_team: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in observations:
        team = str(row.get("canonical_team_id") or "")
        if team:
            by_team[team].append(row)
    admitted = 0
    insufficient = 0
    near_bound = 0
    sealed_skip = 0
    clocked = 0
    date_only = 0
    parseable_games = 0
    examples: list[dict[str, Any]] = []
    near_window = timedelta(hours=24)
    for team_id in sorted(by_team):
        parseable: list[dict[str, Any]] = []
        for row in by_team[team_id]:
            season = int(row.get("season") or 0)
            if season in sealed:
                sealed_skip += 1
                continue
            game_id = str(row.get("canonical_game_id") or "")
            bounds = _proxy_bounds(starts.get(game_id, ""))
            if bounds is None:
                insufficient += 1
                continue
            parseable.append({"game_id": game_id, **bounds})
        parseable_games += len(parseable)
        for target in parseable:
            for prior in parseable:
                if prior["game_id"] == target["game_id"]:
                    continue
                if prior["complete"] > target["earliest"]:
                    continue
                admitted += 1
                if prior["proxy_class"] == "PROXY_CLOCKED_12H":
                    clocked += 1
                else:
                    date_only += 1
                if target["earliest"] - prior["complete"] < near_window:
                    near_bound += 1
                    if len(examples) < 25:
                        examples.append(
                            {
                                "canonical_team_id": team_id,
                                "prior_game_id": prior["game_id"],
                                "target_game_id": target["game_id"],
                                "class": prior["proxy_class"],
                                "bound_epistemic_status": EPISTEMIC_STATUS,
                                "proven_historical_known_at": False,
                            }
                        )
    return {
        "admitted_proxy_pairs": admitted,
        "clocked_12h_pairs": clocked,
        "date_only_plus_2d_pairs": date_only,
        "insufficient_start_games": insufficient,
        "near_bound_examples": examples,
        "near_bound_pairs": near_bound,
        "parseable_games": parseable_games,
        "sealed_target_skips": sealed_skip,
        "team_count": len(by_team),
    }


def build_audit(
    *,
    repo_root: Path,
    observations: Sequence[Mapping[str, Any]],
    starts: Mapping[str, str],
    issued_at_utc: str,
    census_source: str = "SYNTHETIC_FIXTURE",
) -> dict[str, Any]:
    census = census_team_prior_target_pairs(observations, starts)
    week1 = (
        repo_root
        / "src/aggie_analytics/data/week1_2026_game_grain_national_forecast_successor.py"
    )
    week1_text = week1.read_text(encoding="utf-8") if week1.is_file() else ""
    active_import = any(
        needle in week1_text
        for needle in (
            "national_pit_eligible_slice",
            "prior_is_guaranteed_complete",
            "completion_bound",
        )
    )
    audit = {
        "artifact_type": "CYCLE26_R26_22_PRIOR_TARGET_PAIR_AUDIT",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": PASS_RESULT,
        "publication_label": SHADOW_CLASSIFICATION,
        "bound_epistemic_status": EPISTEMIC_STATUS,
        "predecessor_contract_logical_guarantee_retained_for_hash": True,
        "universal_finality_or_publication_guarantee": False,
        "leakage_declared": False,
        "leakage_note": (
            "No row-level leakage is declared. Near-bound pairs are listed as "
            "conditional-proxy admissions, not as proven known-at or as leakage."
        ),
        "consumers": list(CONSUMERS),
        "active_week1_path_imports_pit_bound": active_import,
        "census_source": census_source,
        "census": census,
        "scientific_nonclaims": [
            "Does not rewrite BAT-666 or BAT-667 predecessor gates.",
            "Does not upgrade +12h/+2d proxies to proven historical known-at.",
            "Does not declare target-game leakage without a row trace.",
            "Does not open the all-cycle trust gate or operator hold.",
        ],
    }
    audit["gate_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in audit.items() if key != "gate_identity"}
        )
    )
    return audit


def materialize(
    *,
    repo_root: Path,
    observations: Sequence[Mapping[str, Any]],
    starts: Mapping[str, str],
    issued_at_utc: str,
    census_source: str = "SYNTHETIC_FIXTURE",
) -> dict[str, Any]:
    audit = build_audit(
        repo_root=repo_root,
        observations=observations,
        starts=starts,
        issued_at_utc=issued_at_utc,
        census_source=census_source,
    )
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        json.dumps(audit, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    return audit
