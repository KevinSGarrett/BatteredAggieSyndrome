"""National entity-identity benchmark and 2026 coverage rebound.

Resolve 2026 prospective-cohort participants against the canonical spine using
official NCAA organization identifiers and official season record tuples. The
participant label surface is never used to decide a binding; it is only used to
locate the official organization identifier by exact equality and to supply an
independent gold label for benchmark measurement.
"""

from __future__ import annotations

import hashlib
import html as html_module
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_ID = "NATIONAL-ENTITY-IDENTITY-BENCHMARK-001"
ARTIFACT_ID = "NATIONAL-ENTITY-IDENTITY-BENCHMARK"

_OPTION = re.compile(r'<option[^>]*value="(\d+)"[^>]*>(.*?)</option>', re.S)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAG = re.compile(r"<[^>]+>")
_TEAM_LINK = re.compile(r'href="/teams/(\d+)"')
_ACADEMIC_YEAR = re.compile(r"^(\d{4})-\d{2}$")


class EntityBenchmarkViolation(RuntimeError):
    """Raised when the entity benchmark would violate its contract."""


def parse_instant(value: str | None) -> datetime | None:
    """Parse a strict trailing-Z UTC instant."""
    if not value or not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value[:-1]).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _text(value: str) -> str:
    return html_module.unescape(_TAG.sub("", value)).strip()


def parse_organization_directory(document: str) -> dict[str, int]:
    """Extract the official organization directory embedded in a history page."""
    anchor = document.find('id="org_id_select"')
    if anchor < 0:
        anchor = document.find('name="org_id"')
    if anchor < 0:
        raise EntityBenchmarkViolation(
            "the official document carries no organization directory select element"
        )
    end = document.find("</select>", anchor)
    if end < 0:
        raise EntityBenchmarkViolation("the organization directory select element is unterminated")
    directory: dict[str, int] = {}
    for organization_id, label in _OPTION.findall(document[anchor:end]):
        name = _text(label)
        if not name:
            continue
        directory.setdefault(name, int(organization_id))
    if not directory:
        raise EntityBenchmarkViolation("the organization directory parsed to zero entries")
    return directory


def parse_season_record_series(document: str) -> list[dict[str, Any]]:
    """Extract the per-season official record table from a team-history page."""
    series: list[dict[str, Any]] = []
    for row in _ROW.findall(document):
        cells = [_text(cell) for cell in _CELL.findall(row)]
        if len(cells) < 7:
            continue
        matched = _ACADEMIC_YEAR.match(cells[0])
        if matched is None:
            continue
        try:
            wins, losses, ties = int(cells[4]), int(cells[5]), int(cells[6])
        except ValueError:
            continue
        links = _TEAM_LINK.findall(row)
        series.append(
            {
                "conference": cells[3],
                "division": cells[2],
                "losses": losses,
                "official_academic_year": cells[0],
                "season": int(matched.group(1)),
                "team_season_id": links[0] if links else None,
                "ties": ties,
                "wins": wins,
            }
        )
    series.sort(key=lambda entry: entry["season"])
    return series


def derive_spine_season_records(
    label_rows: Iterable[Mapping[str, Any]],
) -> dict[str, dict[int, tuple[int, int, int]]]:
    """Derive per-team per-season win/loss/tie records from spine outcome labels."""
    counters: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for row in label_rows:
        team = row.get("canonical_team_id")
        season = row.get("season")
        if team is None or season is None:
            continue
        bucket = counters[str(team)][int(season)]
        if row.get("label_tie"):
            bucket[2] += 1
        elif row.get("label_win"):
            bucket[0] += 1
        else:
            bucket[1] += 1
    return {
        team: {season: (record[0], record[1], record[2]) for season, record in seasons.items()}
        for team, seasons in counters.items()
    }


@dataclass(frozen=True)
class SeasonScope:
    minimum_season: int
    maximum_comparable_season: int
    forbidden_seasons: frozenset[int]

    @classmethod
    def from_contract(cls, contract: Mapping[str, Any]) -> SeasonScope:
        scope = contract["season_scope"]
        return cls(
            minimum_season=int(scope["minimum_season"]),
            maximum_comparable_season=int(scope["maximum_comparable_season"]),
            forbidden_seasons=frozenset(int(s) for s in scope["forbidden_seasons"]),
        )

    def admits(self, season: int) -> bool:
        return (
            self.minimum_season <= season <= self.maximum_comparable_season
            and season not in self.forbidden_seasons
        )


def comparable_official_seasons(
    series: Sequence[Mapping[str, Any]], scope: SeasonScope
) -> dict[int, tuple[int, int, int]]:
    """Restrict an official record series to seasons the contract permits comparing."""
    comparable: dict[int, tuple[int, int, int]] = {}
    for entry in series:
        season = int(entry["season"])
        if not scope.admits(season):
            continue
        wins, losses, ties = int(entry["wins"]), int(entry["losses"]), int(entry["ties"])
        if wins + losses + ties == 0:
            continue
        comparable[season] = (wins, losses, ties)
    return comparable


def score_candidates(
    official: Mapping[int, tuple[int, int, int]],
    spine_records: Mapping[str, Mapping[int, tuple[int, int, int]]],
    *,
    excluded_team_ids: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Score every canonical team against one official record series."""
    scored: list[dict[str, Any]] = []
    for team_id, seasons in spine_records.items():
        if team_id in excluded_team_ids:
            continue
        compared = exact = 0
        for season, record in official.items():
            if season not in seasons:
                continue
            compared += 1
            if seasons[season] == record:
                exact += 1
        if compared == 0:
            continue
        scored.append(
            {
                "agreement_rate": round(exact / compared, 6),
                "canonical_team_id": team_id,
                "compared_seasons": compared,
                "exact_matching_seasons": exact,
            }
        )
    scored.sort(
        key=lambda entry: (
            -entry["exact_matching_seasons"],
            -entry["agreement_rate"],
            entry["canonical_team_id"],
        )
    )
    return scored


def apply_acceptance_rules(
    scored: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply the predeclared acceptance tiers to a scored candidate list."""
    rules = contract["acceptance_rules"]
    tiers = {tier["tier_id"]: tier for tier in rules["tiers"]}
    if not scored:
        return {
            "abstention_reason": "NO_CANDIDATE_MET_THE_MINIMUM_EXACT_MATCH_COUNT",
            "canonical_team_id": None,
            "resolution_state": "ABSTAINED",
            "tier_id": None,
        }
    leader = scored[0]
    runner_up = scored[1] if len(scored) > 1 else None
    margin = leader["exact_matching_seasons"] - (
        runner_up["exact_matching_seasons"] if runner_up else 0
    )
    compared = leader["compared_seasons"]

    for tier_id in rules["tier_precedence"]:
        tier = tiers[tier_id]
        minimum = int(tier["minimum_compared_seasons"])
        maximum = tier.get("maximum_compared_seasons")
        if compared < minimum:
            continue
        if maximum is not None and compared > int(maximum):
            continue
        if leader["exact_matching_seasons"] < int(tier["minimum_exact_matching_seasons"]):
            return {
                "abstention_reason": "NO_CANDIDATE_MET_THE_MINIMUM_EXACT_MATCH_COUNT",
                "canonical_team_id": None,
                "resolution_state": "ABSTAINED",
                "tier_id": tier_id,
            }
        if leader["agreement_rate"] < float(tier["minimum_agreement_rate"]):
            return {
                "abstention_reason": "AGREEMENT_RATE_BELOW_THRESHOLD",
                "canonical_team_id": None,
                "resolution_state": "ABSTAINED",
                "tier_id": tier_id,
            }
        if margin < int(tier["minimum_exact_match_margin_over_runner_up"]):
            return {
                "abstention_reason": "AMBIGUOUS_RUNNER_UP_WITHIN_MARGIN",
                "canonical_team_id": None,
                "resolution_state": "ABSTAINED",
                "tier_id": tier_id,
            }
        return {
            "abstention_reason": None,
            "canonical_team_id": leader["canonical_team_id"],
            "resolution_state": tier["verdict_when_satisfied"],
            "tier_id": tier_id,
        }

    return {
        "abstention_reason": "INSUFFICIENT_COMPARABLE_SEASONS",
        "canonical_team_id": None,
        "resolution_state": "ABSTAINED",
        "tier_id": None,
    }


def resolve_organization(
    *,
    official_series: Sequence[Mapping[str, Any]],
    spine_records: Mapping[str, Mapping[int, tuple[int, int, int]]],
    contract: Mapping[str, Any],
    excluded_team_ids: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Resolve one official organization to a canonical team, or abstain."""
    scope = SeasonScope.from_contract(contract)
    official = comparable_official_seasons(official_series, scope)
    scored = score_candidates(official, spine_records, excluded_team_ids=excluded_team_ids)
    verdict = apply_acceptance_rules(scored, contract)
    leader = scored[0] if scored else None
    runner_up = scored[1] if len(scored) > 1 else None
    verdict.update(
        {
            "comparable_official_seasons": len(official),
            "leading_candidate": leader,
            "runner_up_candidate": runner_up,
        }
    )
    return verdict


def shift_series(series: Sequence[Mapping[str, Any]], *, offset: int = 3) -> list[dict[str, Any]]:
    """Deterministically season-shift a record series for the negative control."""
    return [dict(entry, season=int(entry["season"]) + offset) for entry in series]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def payload_identity(rows: Sequence[Mapping[str, Any]]) -> str:
    return sha256_of(list(rows))


def canonical_payload_entry(
    gate: Mapping[str, Any], data_root: Path, name: str
) -> tuple[Path, str]:
    """Resolve a canonical payload through the gate's manifest rather than by convention."""
    manifest_path = data_root / str(gate["manifest"]["relative_path"])
    if not manifest_path.exists():
        raise EntityBenchmarkViolation(f"the manifest is missing at {manifest_path}")
    manifest = read_json(manifest_path)
    for entry in manifest.get("payloads", []):
        if entry.get("name") == name:
            return data_root / str(entry["relative_path"]), str(entry["sha256"])
    raise EntityBenchmarkViolation(
        f"the manifest at {manifest_path} declares no payload named {name!r}"
    )


def load_inputs(
    *,
    contract_path: Path,
    acquisition_path: Path,
    targets_path: Path,
    data_root: Path,
) -> dict[str, Any]:
    """Load every input the benchmark needs from tracked gates and the data root."""
    repository = contract_path.resolve().parents[1]
    contract = read_json(contract_path)
    acquisition = read_json(acquisition_path)
    targets = read_json(targets_path)

    spine_gate = read_json(repository / "artifacts/data_lake/national_tiered_game_spine_gate.json")
    cohort_gate = read_json(
        repository / "artifacts/shadow/prospective_2026_shadow_cohort_gate.json"
    )

    labels_path, _ = canonical_payload_entry(
        spine_gate, data_root, "national_team_outcome_labels.jsonl"
    )
    cohort_path, cohort_sha256 = canonical_payload_entry(
        cohort_gate, data_root, "prospective_2026_shadow_cohort.jsonl"
    )
    for path in (labels_path, cohort_path):
        if not path.exists():
            raise EntityBenchmarkViolation(f"a required canonical payload is missing at {path}")

    declared = str(contract["cohort_rebuild"]["predecessor_payload_root_sha256"])
    if cohort_sha256 != declared:
        raise EntityBenchmarkViolation(
            "the cohort predecessor identity drifted from the contract declaration:"
            f" contract={declared} manifest={cohort_sha256}"
        )

    return {
        "acquisition": acquisition,
        "acquisition_ledger_sha256": hashlib.sha256(acquisition_path.read_bytes()).hexdigest(),
        "cohort_gate": cohort_gate,
        "cohort_rows": read_jsonl(cohort_path),
        "contract": contract,
        "cohort_predecessor_sha256": cohort_sha256,
        "execution_time_utc": str(acquisition["retrieved_at_utc"]),
        "spine_gate": spine_gate,
        "spine_records": derive_spine_season_records(read_jsonl(labels_path)),
        "targets": targets,
    }


def _acquired_series(acquisition: Mapping[str, Any]) -> dict[int, list[dict[str, Any]]]:
    series: dict[int, list[dict[str, Any]]] = {}
    for row in acquisition["acquisitions"]:
        if row.get("acquisition_state") != "ACQUIRED":
            continue
        series[int(row["organization_id"])] = list(row.get("season_record_series") or [])
    return series


def _resolution_rows(
    *,
    contract: Mapping[str, Any],
    targets: Mapping[str, Any],
    series_by_org: Mapping[int, Sequence[Mapping[str, Any]]],
    spine_records: Mapping[str, Mapping[int, tuple[int, int, int]]],
    acquisition: Mapping[str, Any],
) -> list[dict[str, Any]]:
    directory = acquisition.get("official_organization_directory") or {}
    unavailable = {
        int(row["organization_id"]): row.get("reason", "UNKNOWN")
        for row in acquisition["acquisitions"]
        if row.get("acquisition_state") != "ACQUIRED"
    }
    rows: list[dict[str, Any]] = []
    for label, meta in sorted(targets["organization_labels"].items()):
        organization_id = int(meta["organization_id"])
        official_name_matches_label = directory.get(label) == organization_id
        series = series_by_org.get(organization_id)
        if series is None:
            rows.append(
                {
                    "abstention_reason": "OFFICIAL_EVIDENCE_UNAVAILABLE",
                    "canonical_team_id": None,
                    "comparable_official_seasons": 0,
                    "gold_canonical_team_id": meta.get("gold_canonical_team_id"),
                    "leading_candidate": None,
                    "official_evidence_state": "UNAVAILABLE",
                    "official_evidence_unavailable_reason": unavailable.get(
                        organization_id, "NOT_REQUESTED"
                    ),
                    "official_organization_id": organization_id,
                    "official_source_label": label,
                    "official_source_label_matches_directory": official_name_matches_label,
                    "resolution_state": "ABSTAINED",
                    "role": meta["role"],
                    "runner_up_candidate": None,
                    "tier_id": None,
                }
            )
            continue
        verdict = resolve_organization(
            official_series=series, spine_records=spine_records, contract=contract
        )
        verdict.update(
            {
                "gold_canonical_team_id": meta.get("gold_canonical_team_id"),
                "official_evidence_state": "ACQUIRED",
                "official_evidence_unavailable_reason": None,
                "official_organization_id": organization_id,
                "official_source_label": label,
                "official_source_label_matches_directory": official_name_matches_label,
                "role": meta["role"],
            }
        )
        rows.append(verdict)
    rows.sort(key=lambda row: (row["role"], row["official_source_label"]))
    return rows


def _negative_controls(
    *,
    contract: Mapping[str, Any],
    resolution_rows: Sequence[Mapping[str, Any]],
    series_by_org: Mapping[int, Sequence[Mapping[str, Any]]],
    spine_records: Mapping[str, Mapping[int, tuple[int, int, int]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in resolution_rows:
        organization_id = int(row["official_organization_id"])
        series = series_by_org.get(organization_id)
        if series is None:
            continue

        gold = row.get("gold_canonical_team_id")
        if gold:
            held_out = resolve_organization(
                official_series=series,
                spine_records=spine_records,
                contract=contract,
                excluded_team_ids=frozenset({str(gold)}),
            )
            rows.append(
                {
                    "control_id": "HELD_OUT_TRUE_TEAM",
                    "held_out_canonical_team_id": gold,
                    "observed_canonical_team_id": held_out["canonical_team_id"],
                    "observed_resolution_state": held_out["resolution_state"],
                    "official_organization_id": organization_id,
                    "official_source_label": row["official_source_label"],
                    "passed": held_out["resolution_state"] == "ABSTAINED",
                }
            )

        shifted = resolve_organization(
            official_series=shift_series(series),
            spine_records=spine_records,
            contract=contract,
        )
        rows.append(
            {
                "control_id": "SHUFFLED_RECORD_SERIES",
                "observed_canonical_team_id": shifted["canonical_team_id"],
                "observed_resolution_state": shifted["resolution_state"],
                "official_organization_id": organization_id,
                "official_source_label": row["official_source_label"],
                "original_canonical_team_id": row.get("canonical_team_id"),
                "passed": shifted["canonical_team_id"] != row.get("canonical_team_id")
                or shifted["canonical_team_id"] is None,
            }
        )
    rows.sort(key=lambda row: (row["control_id"], row["official_source_label"]))
    return rows


def _abstention_analysis(resolution_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Explain why the resolver abstained, without asserting an unproven cause."""
    by_reason: dict[str, int] = {}
    partial_coverage = 0
    abstained = 0
    for row in resolution_rows:
        if row["canonical_team_id"] is not None:
            continue
        abstained += 1
        reason = str(row.get("abstention_reason"))
        by_reason[reason] = by_reason.get(reason, 0) + 1
        leader = row.get("leading_candidate") or {}
        compared = leader.get("compared_seasons")
        official = row.get("comparable_official_seasons") or 0
        if compared is not None and official and int(compared) < int(official):
            partial_coverage += 1
    return {
        "abstained": abstained,
        "by_reason": dict(sorted(by_reason.items())),
        "leading_candidate_covered_fewer_seasons_than_the_official_source": partial_coverage,
        "observation": (
            "Where the leading canonical candidate covers fewer seasons than the official "
            "source reports, the canonical spine holds only part of that programme's schedule, "
            "so its derived season records cannot equal the official full-season records. The "
            "resolver abstains in that situation rather than binding on partial agreement."
        ),
    }


def _benchmark_metrics(resolution_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    gold_rows = [row for row in resolution_rows if row["role"] == "GOLD_BENCHMARK"]
    accepted = [row for row in gold_rows if row["canonical_team_id"] is not None]
    correct = [
        row for row in accepted if row["canonical_team_id"] == row["gold_canonical_team_id"]
    ]
    conflicting = [
        row for row in accepted if row["canonical_team_id"] != row["gold_canonical_team_id"]
    ]
    abstained = [row for row in gold_rows if row["canonical_team_id"] is None]
    evaluated = len(gold_rows)

    def ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 6) if denominator else None

    return {
        "abstained": len(abstained),
        "abstention_rate": ratio(len(abstained), evaluated),
        "accepted_bindings": len(accepted),
        "conflict_rate": ratio(len(conflicting), len(accepted)),
        "conflicting_bindings": len(conflicting),
        "correct_bindings": len(correct),
        "exact_match_coverage": ratio(len(accepted), evaluated),
        "gold_organizations_evaluated": evaluated,
        "precision": ratio(len(correct), len(accepted)),
        "recall": ratio(len(correct), evaluated),
    }


def _rebuild_cohort(
    *,
    contract: Mapping[str, Any],
    cohort_rows: Sequence[Mapping[str, Any]],
    resolution_rows: Sequence[Mapping[str, Any]],
    execution_time_utc: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bindings = {
        row["official_source_label"]: row
        for row in resolution_rows
        if row["canonical_team_id"] is not None
    }
    preservation = contract["cohort_rebuild"]["checkpoint_preservation"]

    executed_at = parse_instant(execution_time_utc)
    successors: list[dict[str, Any]] = []
    newly_supported_participants = 0
    newly_supported_contests = 0
    newly_supported_with_an_open_checkpoint = 0
    still_unsupported_contests = 0

    for row in cohort_rows:
        successor = json.loads(json.dumps(row, sort_keys=True))
        upgraded_here = 0
        for key in ("participants", "home_team", "away_team"):
            value = successor.get(key)
            entries = value if isinstance(value, list) else [value] if value else []
            for entry in entries:
                if entry.get("canonical_team_id"):
                    continue
                binding = bindings.get(entry.get("source_display_name"))
                if binding is None:
                    continue
                entry["canonical_team_id"] = binding["canonical_team_id"]
                entry["official_organization_id"] = binding["official_organization_id"]
                entry["resolution_state"] = binding["resolution_state"]
                entry["resolution_evidence"] = "OFFICIAL_NCAA_ORGANIZATION_RECORD_TUPLE"
                if key == "participants":
                    upgraded_here += 1

        remaining = [
            entry.get("source_display_name")
            for entry in successor.get("participants") or []
            if not entry.get("canonical_team_id")
        ]
        successor["unresolved_participant_names"] = sorted(name for name in remaining if name)
        newly_supported_participants += upgraded_here

        open_checkpoints: list[str] = []
        for checkpoint in successor.get("checkpoints") or []:
            deadline = parse_instant(str(checkpoint.get("deadline_utc")))
            elapsed = deadline is not None and deadline <= executed_at
            checkpoint["deadline_elapsed_at_successor_execution_time"] = elapsed
            checkpoint["successor_execution_time_utc"] = execution_time_utc
            if not elapsed:
                open_checkpoints.append(str(checkpoint.get("checkpoint_id")))

        was_unsupported = row.get("cohort_state") == "UNSUPPORTED_ENTITY"
        if was_unsupported and not remaining:
            newly_supported_contests += 1
            successor["entity_support_state"] = "SUPPORTED_BY_OFFICIAL_RECORD_TUPLE"
            if open_checkpoints:
                newly_supported_with_an_open_checkpoint += 1
                successor["cohort_state"] = "ENTITY_SUPPORTED_WITH_A_CHECKPOINT_STILL_OPEN"
                successor["state_reason"] = (
                    "ENTITY_SUPPORT_WAS_ESTABLISHED_WHILE_"
                    + "_AND_".join(sorted(open_checkpoints))
                    + "_REMAINS_OPEN_AND_THIS_ARTIFACT_MUST_NOT_EXECUTE_IT_EARLY"
                )
            else:
                successor["cohort_state"] = "ENTITY_SUPPORTED_BUT_PREGAME_CHECKPOINTS_ELAPSED"
                successor["state_reason"] = (
                    "ENTITY_SUPPORT_WAS_ESTABLISHED_AFTER_EVERY_DECLARED_PREGAME_CHECKPOINT_"
                    "SO_NO_FORECAST_MAY_BE_CREATED"
                )
            successor["open_checkpoints_at_successor_execution_time"] = sorted(open_checkpoints)
        elif was_unsupported:
            still_unsupported_contests += 1
            successor["entity_support_state"] = "UNSUPPORTED_ENTITY"
        else:
            successor["entity_support_state"] = "SUPPORTED_BY_EXACT_NORMALIZED_NAME"

        for checkpoint in successor.get("checkpoints") or []:
            checkpoint["preservation_policy"] = preservation.get(
                checkpoint.get("checkpoint_id"), "PRESERVE_AS_IS"
            )
        successors.append(successor)

    successors.sort(key=lambda entry: str(entry.get("ncaa_contest_id")))
    rebound = {
        "execution_time_utc": execution_time_utc,
        "frozen_or_scorable_coverage_changed": False,
        "frozen_or_scorable_coverage_explanation": (
            "This artifact resolves identities only. It creates no snapshot and no forecast, "
            "and it never creates a forecast retroactively, so no contest became frozen or "
            "scorable as a result of the rebound. Newly supported contests that still hold an "
            "open checkpoint become eligible for a future precommitment, which this artifact "
            "deliberately does not execute early."
        ),
        "newly_supported_contests": newly_supported_contests,
        "newly_supported_participants": newly_supported_participants,
        "newly_supported_with_an_open_checkpoint": newly_supported_with_an_open_checkpoint,
        "newly_supported_with_every_checkpoint_elapsed": (
            newly_supported_contests - newly_supported_with_an_open_checkpoint
        ),
        "predecessor_payload_root_sha256": contract["cohort_rebuild"][
            "predecessor_payload_root_sha256"
        ],
        "still_unsupported_contests": still_unsupported_contests,
    }
    return successors, rebound


def build_artifact(
    *,
    acquisition: Mapping[str, Any],
    acquisition_ledger_sha256: str,
    cohort_gate: Mapping[str, Any],
    cohort_predecessor_sha256: str,
    cohort_rows: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
    execution_time_utc: str,
    spine_gate: Mapping[str, Any],
    spine_records: Mapping[str, Mapping[int, tuple[int, int, int]]],
    targets: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the benchmark gate and its payloads."""
    scope = SeasonScope.from_contract(contract)
    if scope.forbidden_seasons != frozenset({2024, 2025}):
        raise EntityBenchmarkViolation(
            "the contract must declare exactly the 2024 and 2025 seasons as sealed,"
            f" not {sorted(scope.forbidden_seasons)}"
        )
    if scope.maximum_comparable_season > 2023:
        raise EntityBenchmarkViolation(
            "the maximum comparable season must not reach a sealed season,"
            f" got {scope.maximum_comparable_season}"
        )

    series_by_org = _acquired_series(acquisition)
    sealed_offered = sorted(
        {
            int(entry["season"])
            for series in series_by_org.values()
            for entry in series
            if int(entry["season"]) in scope.forbidden_seasons
        }
    )

    resolution_rows = _resolution_rows(
        contract=contract,
        targets=targets,
        series_by_org=series_by_org,
        spine_records=spine_records,
        acquisition=acquisition,
    )
    controls = _negative_controls(
        contract=contract,
        resolution_rows=resolution_rows,
        series_by_org=series_by_org,
        spine_records=spine_records,
    )
    metrics = _benchmark_metrics(resolution_rows)
    if parse_instant(execution_time_utc) is None:
        raise EntityBenchmarkViolation(
            f"the execution time must be a trailing-Z UTC instant, got {execution_time_utc!r}"
        )
    successors, rebound = _rebuild_cohort(
        contract=contract,
        cohort_rows=cohort_rows,
        resolution_rows=resolution_rows,
        execution_time_utc=execution_time_utc,
    )

    unresolved_rows = [row for row in resolution_rows if row["role"] == "UNRESOLVED_TARGET"]
    payloads = {
        "national_entity_identity_resolutions.jsonl": resolution_rows,
        "national_entity_identity_negative_controls.jsonl": controls,
        "prospective_2026_shadow_cohort_successor.jsonl": successors,
    }
    payload_hashes = {name: payload_identity(rows) for name, rows in payloads.items()}

    gate = {
        "abstention_analysis": _abstention_analysis(resolution_rows),
        "acquisition_evidence": {
            "ledger_sha256": acquisition_ledger_sha256,
            "official_source_id": contract["official_source"]["source_id"],
            "organizations_acquired": len(series_by_org),
            "organizations_requested": len(targets["organization_ids"]),
            "retrieved_at_utc": execution_time_utc,
        },
        "artifact_id": ARTIFACT_ID,
        "authority": {
            "champion_or_production_promotion": False,
            "fuzzy_auto_accept_enabled": False,
            "historical_known_at_authority_established": False,
            "identity_bound_without_official_evidence": False,
            "protected_lane_admission": False,
        },
        "benchmark_metrics": metrics,
        "classification": (
            "CROSS_SOURCE_NATIONAL_ENTITY_IDENTITY_BENCHMARK_AND_2026_COVERAGE_REBOUND"
        ),
        "cohort_successor": {
            "immutable_successor_of": cohort_gate["contract_id"],
            "predecessor_gate_identity": cohort_gate["gate_identity"],
            "predecessor_is_rewritten": False,
            "predecessor_payload_sha256": cohort_predecessor_sha256,
            "rows": len(successors),
        },
        "contract_id": CONTRACT_ID,
        "coverage_rebound": rebound,
        "decision_unit": contract["decision_unit"],
        "execution_time_utc": execution_time_utc,
        "forbidden_seasons_compared": 0,
        "forbidden_seasons_offered_by_the_source_and_discarded": sealed_offered,
        "gap_reference": contract["gap_reference"],
        "identity_surfaces": {
            "fuzzy_auto_accept_enabled": False,
            "official_directory_entries": len(
                acquisition.get("official_organization_directory") or {}
            ),
            "organizations_acquired": len(series_by_org),
            "organizations_requested": len(targets["organization_ids"]),
        },
        "jira_key": contract["jira_key"],
        "lane": "PROSPECTIVE_SHADOW_OBSERVATION_ONLY",
        "negative_controls": {
            "evaluated": len(controls),
            "failed": sum(1 for row in controls if not row["passed"]),
            "passed": sum(1 for row in controls if row["passed"]),
        },
        "payload_root_sha256": sha256_of(payload_hashes),
        "payloads": [
            {"name": name, "rows": len(payloads[name]), "sha256": digest}
            for name, digest in sorted(payload_hashes.items())
        ],
        "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
        "protected_lane_opened": False,
        "scientific_non_claims": list(contract["scientific_non_claims"]),
        "scientific_nonclaims": {
            "bas_or_aggie_excess": False,
            "causal_effect": False,
            "champion_or_production_selection": False,
            "every_unresolved_participant_was_resolved": False,
            "fuzzy_similarity_acceptance_enabled": False,
            "gap_002_closed_by_this_benchmark": False,
            "gap_009_closed_by_this_benchmark": False,
            "new_frozen_or_scorable_coverage_created": False,
            "protected_performance": False,
            "retroactive_forecast_created": False,
            "specialization_lift": False,
        },
        "season_scope": {
            "forbidden_seasons": sorted(scope.forbidden_seasons),
            "maximum_comparable_season": scope.maximum_comparable_season,
            "minimum_season": scope.minimum_season,
        },
        "spine_dataset_identity": spine_gate["dataset_identity"],
        "unresolved_target_outcome": {
            "abstained": sum(1 for row in unresolved_rows if row["canonical_team_id"] is None),
            "evaluated": len(unresolved_rows),
            "resolved": sum(
                1 for row in unresolved_rows if row["canonical_team_id"] is not None
            ),
        },
    }
    gate["gate_identity"] = sha256_of(gate)
    return {"gate": gate, "payloads": payloads}
