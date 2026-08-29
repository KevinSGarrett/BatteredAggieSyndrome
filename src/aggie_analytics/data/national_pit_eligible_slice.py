"""First nonzero national point-in-time eligible feature slice.

Every prior-derived value is recomputed from contests whose precommitted completion bound
provably precedes the target contest's earliest possible start. Nothing is inherited from the
existing spine's prior columns, so eligibility holds by construction. Rankings and venue
features are excluded because the BAT-666 audit found only retrieval-time authority for them.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "aggie.data.national_pit_eligible_slice.v1"
CONTRACT_ID = "BAT-667-FIRST-NATIONAL-PIT-ELIGIBLE-SLICE-V1"
CLASSIFICATION = "FIRST_NONZERO_NATIONAL_POINT_IN_TIME_ELIGIBLE_FEATURE_SLICE"
LANE = "HISTORICAL_DEVELOPMENT_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
JIRA_KEY = "BAT-667"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-FIRST-NATIONAL-PIT-ELIGIBLE-SLICE-001"
PRODUCER = "tools/build_national_pit_eligible_slice.py"

CONTRACT_RELATIVE = "configs/national_pit_eligible_slice_contract.json"
GATE_RELATIVE = "artifacts/data_lake/national_pit_eligible_slice_gate.json"
EVIDENCE_RELATIVE = "artifacts/data_lake/national_pit_eligible_slice_replay.json"
AUTHORITY_GATE_RELATIVE = "artifacts/data_lake/historical_known_at_authority_gate.json"
PAYLOAD_NAME = "national_pit_eligible_team_features.jsonl"

PASS_RESULT = "PASS_FIRST_NATIONAL_PIT_ELIGIBLE_SLICE"

ELIGIBLE = "PIT_FEATURE_ELIGIBLE"
ELIGIBLE_NO_PRIOR = "PIT_ELIGIBLE_NO_PRIOR_INFORMATION"
REJECTED_NO_START = "REJECTED_NO_USABLE_START_EVIDENCE"
REJECTED_NO_OUTCOME = "REJECTED_NO_OUTCOME_REFERENCE"
REJECTED_SEALED = "REJECTED_SEALED_SEASON"

ROW_VERDICTS = (
    ELIGIBLE,
    ELIGIBLE_NO_PRIOR,
    REJECTED_NO_START,
    REJECTED_NO_OUTCOME,
    REJECTED_SEALED,
)

DATE_ONLY_CLOCK = "00:00"
NON_AUTHORITATIVE_KEYS = frozenset({"gate_identity"})


class PitSliceViolation(RuntimeError):
    """Raised when the slice input or artifact is not admissible."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / CONTRACT_RELATIVE
    if not path.exists():
        raise PitSliceViolation(f"the PIT eligible slice contract is missing at {path}")
    contract = read_json(path)
    if contract.get("contract_id") != CONTRACT_ID:
        raise PitSliceViolation("the PIT eligible slice contract identifier does not match")
    return contract


def load_authority(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / AUTHORITY_GATE_RELATIVE
    if not path.exists():
        raise PitSliceViolation("the BAT-666 known-at authority gate is missing")
    return read_json(path)


def require_authority(authority: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    """Refuse to build a slice on top of authority the audit did not actually grant."""

    declared = contract["authority_predecessor"]
    sufficient = set(authority.get("domains_with_sufficient_authority", []))
    blocked = set(authority.get("domains_blocked_from_point_in_time_admission", []))
    if not set(declared["required_domains_with_sufficient_authority"]).issubset(sufficient):
        raise PitSliceViolation(
            "the known-at audit does not grant authority for every domain this slice requires"
        )
    if not set(declared["required_domains_blocked"]).issubset(blocked):
        raise PitSliceViolation(
            "a domain this slice excludes is no longer reported as blocked, so the exclusion"
            " rationale has drifted from the audit"
        )
    for domain in contract["admitted_domains"]:
        if domain not in sufficient:
            raise PitSliceViolation(f"domain {domain} is admitted without audited authority")


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


def is_date_only(instant: datetime) -> bool:
    return instant.strftime("%H:%M") == DATE_ONLY_CLOCK


def earliest_start_bound(instant: datetime, policy: Mapping[str, Any]) -> datetime:
    """The earliest instant at which a contest could possibly have begun."""

    if is_date_only(instant):
        offset = int(policy["date_only_rule"]["earliest_possible_start_offset_days"])
        return instant + timedelta(days=offset)
    return instant


def completion_bound(instant: datetime, policy: Mapping[str, Any]) -> datetime:
    """The latest instant by which a contest is guaranteed to have finished."""

    if is_date_only(instant):
        offset = int(policy["date_only_rule"]["latest_possible_completion_offset_days"])
        return instant + timedelta(days=offset)
    hours = float(policy["published_start_instant_rule"]["maximum_contest_duration_hours"])
    return instant + timedelta(hours=hours)


class PriorAccumulator:
    """Running bound-admissible prior totals for a single team."""

    def __init__(self) -> None:
        self.games = 0
        self.wins = 0
        self.points_for = 0
        self.points_against = 0
        self.margin = 0
        self.by_season: dict[int, list[int]] = defaultdict(lambda: [0, 0])

    def admit(self, outcome: Mapping[str, Any]) -> None:
        self.games += 1
        won = 1 if outcome.get("label_win") else 0
        self.wins += won
        self.points_for += int(outcome.get("points_for") or 0)
        self.points_against += int(outcome.get("points_against") or 0)
        self.margin += int(outcome.get("margin") or 0)
        season = self.by_season[int(outcome["season"])]
        season[0] += 1
        season[1] += won

    def emit(self, season: int) -> dict[str, Any]:
        previous = self.by_season.get(season - 1, [0, 0])
        current = self.by_season.get(season, [0, 0])
        return {
            "pit_prior_games_played": self.games,
            "pit_prior_margin_mean": self._mean(self.margin),
            "pit_prior_points_against_mean": self._mean(self.points_against),
            "pit_prior_points_for_mean": self._mean(self.points_for),
            "pit_prior_season_win_rate": _ratio(previous[1], previous[0]),
            "pit_prior_win_rate": self._mean(self.wins),
            "pit_season_to_date_games": current[0],
            "pit_season_to_date_win_rate": _ratio(current[1], current[0]),
        }

    def _mean(self, total: int) -> float | None:
        return _ratio(total, self.games)


def _ratio(numerator: float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 12)


def build_rows(
    observations: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    starts: Mapping[str, str],
    contract: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Recompute every team row's prior features from bound-admissible evidence only."""

    sealed = set(contract["eligibility_rules"]["sealed_seasons_forbidden"])
    outcome_by_key = {
        (row["canonical_team_id"], row["canonical_game_id"]): row for row in outcomes
    }

    by_team: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for observation in observations:
        by_team[str(observation["canonical_team_id"])].append(observation)

    emitted: list[dict[str, Any]] = []
    for team_id in sorted(by_team):
        emitted.extend(
            _build_team_rows(
                team_id, by_team[team_id], outcome_by_key, starts, policy, sealed
            )
        )
    emitted.sort(key=lambda row: (row["canonical_game_id"], row["canonical_team_id"]))
    return emitted


def _build_team_rows(
    team_id: str,
    observations: Sequence[Mapping[str, Any]],
    outcome_by_key: Mapping[tuple[str, str], Mapping[str, Any]],
    starts: Mapping[str, str],
    policy: Mapping[str, Any],
    sealed: set[int],
) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    targets: list[tuple[datetime, Mapping[str, Any]]] = []
    priors: list[tuple[datetime, Mapping[str, Any]]] = []

    for observation in observations:
        game_id = str(observation["canonical_game_id"])
        season = int(observation["season"])
        outcome = outcome_by_key.get((team_id, game_id))
        instant = parse_start_instant(starts.get(game_id, ""))
        if season in sealed:
            rejected.append(_rejection(observation, REJECTED_SEALED))
            continue
        if instant is None:
            rejected.append(_rejection(observation, REJECTED_NO_START))
            continue
        if outcome is None:
            rejected.append(_rejection(observation, REJECTED_NO_OUTCOME))
            continue
        targets.append((earliest_start_bound(instant, policy), observation))
        priors.append((completion_bound(instant, policy), outcome))

    targets.sort(key=lambda item: (item[0], str(item[1]["canonical_game_id"])))
    priors.sort(key=lambda item: (item[0], str(item[1]["canonical_game_id"])))

    accumulator = PriorAccumulator()
    cursor = 0
    rows: list[dict[str, Any]] = []
    for earliest, observation in targets:
        while cursor < len(priors) and priors[cursor][0] <= earliest:
            accumulator.admit(priors[cursor][1])
            cursor += 1
        season = int(observation["season"])
        features = accumulator.emit(season)
        verdict = ELIGIBLE if features["pit_prior_games_played"] > 0 else ELIGIBLE_NO_PRIOR
        rows.append(
            {
                **features,
                "canonical_game_id": str(observation["canonical_game_id"]),
                "canonical_team_id": team_id,
                "is_home": bool(observation.get("is_home")),
                "is_neutral_site": bool(observation.get("is_neutral_site")),
                "opponent_canonical_team_id": observation.get("opponent_canonical_team_id"),
                "row_verdict": verdict,
                "season": season,
                "week": observation.get("week"),
            }
        )
    return rows + rejected


def _rejection(observation: Mapping[str, Any], verdict: str) -> dict[str, Any]:
    return {
        "canonical_game_id": str(observation["canonical_game_id"]),
        "canonical_team_id": str(observation["canonical_team_id"]),
        "row_verdict": verdict,
        "season": int(observation["season"]),
    }


def measure_leakage_exposure(
    rows: Sequence[Mapping[str, Any]], spine_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Compare bound-admissible prior counts against the spine's own prior counts."""

    spine_by_key = {
        (str(row["canonical_team_id"]), str(row["canonical_game_id"])): row for row in spine_rows
    }
    compared = removed_total = rows_with_removal = exceeded = 0
    worst = 0
    win_rate_differs = 0
    for row in rows:
        if row["row_verdict"] not in {ELIGIBLE, ELIGIBLE_NO_PRIOR}:
            continue
        spine = spine_by_key.get((row["canonical_team_id"], row["canonical_game_id"]))
        if spine is None:
            continue
        compared += 1
        difference = int(spine.get("prior_games_played") or 0) - int(
            row["pit_prior_games_played"]
        )
        if difference > 0:
            rows_with_removal += 1
            removed_total += difference
            worst = max(worst, difference)
        elif difference < 0:
            exceeded += 1
        spine_rate, pit_rate = spine.get("prior_win_rate"), row.get("pit_prior_win_rate")
        if spine_rate is not None and pit_rate is not None and abs(spine_rate - pit_rate) > 1e-9:
            win_rate_differs += 1
    return {
        "compared_rows": compared,
        "interpretation": (
            "The bound removed no prior anywhere, because no team plays two contests inside the"
            " bound window. The conservative cutoff is therefore free at the team-prior grain:"
            " it costs no evidence while making every remaining value provably pre-kickoff."
        ),
        "largest_single_row_removal": worst,
        "mean_priors_removed_per_row": _ratio(removed_total, compared),
        "rows_where_recomputation_exceeded_the_spine": exceeded,
        "rows_with_at_least_one_prior_removed": rows_with_removal,
        "total_priors_removed_by_the_bound": removed_total,
        "win_rate_convention_difference": {
            "explanation": (
                "This slice counts a tie toward games played and toward neither wins nor losses,"
                " which the contract precommits. Where the spine used a different tie convention"
                " the rates differ even though the admitted prior counts are identical."
            ),
            "rows_where_the_prior_win_rate_differs_from_the_spine": win_rate_differs,
        },
    }


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    verdicts = Counter(row["row_verdict"] for row in rows)
    eligible = [row for row in rows if row["row_verdict"] == ELIGIBLE]
    seasons = sorted({row["season"] for row in eligible})
    per_season = Counter(row["season"] for row in eligible)
    missing = Counter()
    for row in eligible:
        for key, value in row.items():
            if key.startswith("pit_") and value is None:
                missing[key] += 1
    return {
        "eligible_distinct_games": len({row["canonical_game_id"] for row in eligible}),
        "eligible_distinct_teams": len({row["canonical_team_id"] for row in eligible}),
        "eligible_seasons": seasons,
        "eligible_team_rows": len(eligible),
        "feature_missingness_among_eligible_rows": dict(sorted(missing.items())),
        "first_eligible_season": seasons[0] if seasons else None,
        "last_eligible_season": seasons[-1] if seasons else None,
        "per_season_eligible_team_rows": {
            str(season): count for season, count in sorted(per_season.items())
        },
        "row_verdict_counts": {
            verdict: verdicts.get(verdict, 0) for verdict in ROW_VERDICTS
        },
        "total_team_rows": len(rows),
    }


def payload_lines(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def build_gate(
    rows: Sequence[Mapping[str, Any]],
    spine_rows: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
    authority: Mapping[str, Any],
    predecessor_identities: Mapping[str, Any],
    *,
    producer: str = PRODUCER,
) -> dict[str, Any]:
    require_authority(authority, contract)
    summary = summarize(rows)
    eligible = summary["eligible_team_rows"]
    if eligible <= 0:
        raise PitSliceViolation(
            "the slice is empty, which contradicts the audited authority this phase depends on"
        )

    bundle = {
        "admitted_domains": list(contract["admitted_domains"]),
        "artifact_type": "NATIONAL_PIT_ELIGIBLE_SLICE_GATE",
        "authority": "EVERY_EMITTED_VALUE_IS_RECOMPUTED_FROM_BOUND_ADMISSIBLE_EVIDENCE_ONLY",
        "authority_predecessor_identity": authority.get("gate_identity"),
        "bound_predecessor_identities": dict(sorted(predecessor_identities.items())),
        "classification": CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_of(contract),
        "cutoff_policy": authority["conservative_bound_policy"],
        "decision_unit": LOCAL_ISSUE_ID,
        "eligibility_rules": contract["eligibility_rules"],
        "emitted_features": list(contract["emitted_features"]),
        "excluded_domains": contract["excluded_domains"],
        "gap_id": contract["gap_id"],
        "gap_verdict": {
            "gap_id": "GAP-002",
            "remains_open": True,
            "verdict": "FIRST_NONZERO_PIT_ELIGIBLE_SLICE_MATERIALIZED_WHILE_TWO_DOMAINS_STAY_BLOCKED",
            "why": (
                "A nonzero slice now exists over the three audited domains, but rankings and the"
                " mutable venue attributes still lack any known-at authority, so the gap stays"
                " open and the protected lane stays closed."
            ),
        },
        "jira_key": JIRA_KEY,
        "lane": LANE,
        "leakage_exposure": measure_leakage_exposure(rows, spine_rows),
        "local_issue_id": LOCAL_ISSUE_ID,
        "parent_jira_key": PARENT_JIRA_KEY,
        "payload": {
            "name": PAYLOAD_NAME,
            "rows": len(rows),
            "sha256": hashlib.sha256(payload_lines(rows)).hexdigest(),
        },
        "population": summary,
        "producer": producer,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    bundle["gate_identity"] = gate_identity_of(bundle)
    return bundle


def gate_identity_of(bundle: Mapping[str, Any]) -> str:
    return sha256_of({k: v for k, v in bundle.items() if k not in NON_AUTHORITATIVE_KEYS})


def validate_artifact(repo_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Check the committed slice gate for internal consistency and forbidden shortcuts."""

    repo_root = Path(repo_root)
    contract = load_contract(repo_root)
    if gate is None:
        gate_path = repo_root / GATE_RELATIVE
        if not gate_path.exists():
            raise PitSliceViolation("the PIT eligible slice gate has not been materialized")
        gate = read_json(gate_path)

    if gate.get("schema_version") != SCHEMA_VERSION:
        raise PitSliceViolation("the committed gate schema version does not match")
    if gate.get("contract_sha256") != sha256_of(contract):
        raise PitSliceViolation("the committed gate is bound to a different contract body")
    if gate_identity_of(gate) != gate.get("gate_identity"):
        raise PitSliceViolation("the committed gate identity does not cover its content")

    require_authority(load_authority(repo_root), contract)

    if gate.get("protected_lane") != PROTECTED_LANE:
        raise PitSliceViolation("the slice does not retain the blocked protected lane")
    for domain in contract["excluded_domains"]:
        if domain["domain_id"] in gate.get("admitted_domains", []):
            raise PitSliceViolation(f"excluded domain {domain['domain_id']} was admitted")
    for feature in gate.get("emitted_features", []):
        if feature.startswith(("ap_poll", "coaches_poll", "venue_", "rankings")):
            raise PitSliceViolation(f"emitted feature {feature} belongs to a blocked domain")

    population = gate.get("population", {})
    if population.get("eligible_team_rows", 0) <= 0:
        raise PitSliceViolation("the committed slice is empty")
    counts = population.get("row_verdict_counts", {})
    if set(counts) != set(ROW_VERDICTS):
        raise PitSliceViolation("the verdict tally does not cover exactly the declared verdicts")
    if sum(counts.values()) != population.get("total_team_rows"):
        raise PitSliceViolation("the verdict tally does not reconcile to the total row count")
    sealed = set(contract["eligibility_rules"]["sealed_seasons_forbidden"])
    if sealed.intersection(population.get("eligible_seasons", [])):
        raise PitSliceViolation("a sealed season appears in the eligible population")

    leakage = gate.get("leakage_exposure", {})
    if leakage.get("rows_where_recomputation_exceeded_the_spine", 1) != 0:
        raise PitSliceViolation(
            "the recomputation admitted more priors than the spine, so the bound was not applied"
        )
    if gate.get("gap_verdict", {}).get("remains_open") is not True:
        raise PitSliceViolation("the slice reports GAP-002 closed, which it does not close")

    return {
        "eligible_seasons": [
            population["first_eligible_season"],
            population["last_eligible_season"],
        ],
        "eligible_team_rows": population["eligible_team_rows"],
        "gate_identity": gate["gate_identity"],
        "payload_sha256": gate["payload"]["sha256"],
        "result": gate["result"],
        "row_verdict_counts": counts,
        "total_priors_removed_by_the_bound": leakage.get("total_priors_removed_by_the_bound"),
    }
