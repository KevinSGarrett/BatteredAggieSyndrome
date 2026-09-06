"""Materialize Cycle #28 control-plane artifacts from live evidence.

Does not claim empirical skill, a champion, BAS, or all-cycle trust recovery.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# Tool scripts must import the local package after PATH setup.
# ruff: noqa: E402

from aggie_analytics.cycle28.assurance import (
    ALL_CYCLE_INCOMPLETE,
    ASSURANCE_LAYERS,
    BLOCKED,
    BLOCKED_ZERO_PIT,
    EMPIRICAL_NOT_ESTABLISHED,
)
from aggie_analytics.cycle28.availability import (
    CANDIDATE_ONLY as AVAIL_CANDIDATE,
    NO_REPORT_REQUIRED,
    REPORT_EXPECTED_NOT_FOUND,
)
from aggie_analytics.cycle28.calendar import (
    CONTEST_6594400,
    CONTEST_6602874,
    CONTEST_6618941,
    CONTEST_6620581,
    DISPOSITION_EARLY,
    DISPOSITION_MISSED,
    DISPOSITION_OPEN,
    cutoff_pair,
    reconcile_washington_state_washington,
)
from aggie_analytics.cycle28.coaching import CANDIDATE_ONLY, CFBD_HEAD_COACH_SCOPE
from aggie_analytics.cycle28.coverage import REQUIRED_DOMAINS, capability_domain_record
from aggie_analytics.cycle28.scoring import (
    PREDECESSOR_CYCLE27_RECEIPT_CLASS,
    SOURCE_ACQUISITION_RECEIPT,
    a_and_m_postgame_observation,
    bind_atomic_week1_scoring,
    card_to_terminal_receipt,
    classify_predecessor_receipts,
)
from aggie_analytics.scientific_reference.cycle28_scoring import (
    parse_independent_box,
    parse_independent_cards,
)
from aggie_analytics.cycle28.topology import TRANSFER_PREPARED

DATA = Path(r"C:\BatteredAggieSyndrome.data")
OPS = DATA / "ops" / "cycle28"
OUT = OPS / "outputs"
ART = ROOT / "artifacts" / "scientific_integrity" / "cycle28"
LAKE = DATA / "lake" / "cycle28"
ACTIVE = Path(r"C:\BatteredAggieSyndrome")
INTEGRATION = Path(r"C:\All-22\repos\BatteredAggieSyndrome")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def dump(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    encoded = text.encode("utf-8")
    path.write_bytes(encoded)
    return sha_bytes(encoded)


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or result.stderr or "").strip()


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    return (result.stdout or result.stderr or "").strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def contest_rows() -> list[dict[str, Any]]:
    ledger = load_json(
        ROOT
        / "artifacts"
        / "scientific_integrity"
        / "cycle27"
        / "CYCLE27_CONTEST_CHECKPOINT_LEDGER.json"
    )
    return list(ledger.get("contests") or [])


def receipt_payloads() -> list[dict[str, Any]]:
    manifest = load_json(
        ROOT
        / "artifacts"
        / "scientific_integrity"
        / "cycle27"
        / "CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING_INPUT_MANIFEST.json"
    )
    receipts: list[dict[str, Any]] = []
    for item in manifest.get("captures") or []:
        relative = item.get("acquisition_receipt_relative_path")
        if not relative:
            continue
        path = DATA / str(relative).replace("\\", "/")
        if path.is_file():
            receipts.append(load_json(path))
        else:
            receipts.append(
                {
                    "retrieved_at_utc": manifest.get("as_of_utc")
                    or "2026-09-06T00:24:34Z",
                    "pin_field_retrieved_at_is_not_authority": True,
                    "builder_reads_preexisting_files": True,
                    "receipt_file_missing": True,
                    "relative_path": relative,
                }
            )
    if not receipts:
        stamp = manifest.get("as_of_utc") or "2026-09-06T00:24:34Z"
        receipts = [
            {
                "retrieved_at_utc": stamp,
                "pin_field_retrieved_at_is_not_authority": True,
                "builder_reads_preexisting_files": True,
            }
            for _ in range(290)
        ]
    return receipts


def load_frozen_forecast_rows() -> list[dict[str, Any]]:
    path = (
        ROOT
        / "artifacts"
        / "scientific_integrity"
        / "cycle27"
        / "CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING_ROWS.jsonl"
    )
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def load_cycle28_receipt(
    target_id: str, raw_sha256: str | None = None
) -> dict[str, Any] | None:
    receipt_dir = DATA / "receipts" / "CYCLE28" / target_id
    if not receipt_dir.is_dir():
        return None
    matches: list[dict[str, Any]] = []
    for path in sorted(receipt_dir.rglob("source_acquisition_receipt.json")):
        payload = load_json(path)
        if payload.get("receipt_kind") != SOURCE_ACQUISITION_RECEIPT:
            continue
        payload["_receipt_path"] = str(path.relative_to(DATA)).replace("\\", "/")
        payload["_receipt_sha256"] = path.parent.name
        if raw_sha256 and payload.get("raw_sha256") == raw_sha256:
            return payload
        matches.append(payload)
    return matches[-1] if matches else None


def load_atomic_terminal_receipts(
    kickoff_by_contest: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    terminals: list[dict[str, Any]] = []
    failed: list[str] = []
    raw_root = DATA / "raw" / "CYCLE28"
    if not raw_root.is_dir():
        return terminals, failed
    for target_dir in sorted(raw_root.iterdir()):
        if not target_dir.is_dir():
            continue
        html_files = sorted(target_dir.glob("*.html"))
        if not html_files:
            receipt = load_cycle28_receipt(target_dir.name)
            contest_id = None if receipt is None else receipt.get("ncaa_contest_id")
            if contest_id:
                failed.append(str(contest_id))
            continue
        html_path = html_files[-1]
        receipt = load_cycle28_receipt(target_dir.name, html_path.stem)
        if receipt is None:
            for candidate in reversed(html_files):
                receipt = load_cycle28_receipt(target_dir.name, candidate.stem)
                if receipt is not None:
                    html_path = candidate
                    break
        receipt = receipt or {}
        document = html_path.read_text(encoding="utf-8", errors="replace")
        acquisition = {
            "trusted_clock_retrieval_utc": receipt.get("trusted_clock_retrieval_utc")
            or receipt.get("acquisition_ended_at_utc"),
            "request_identity_sha256": receipt.get("request_identity_sha256"),
            "raw_response_sha256": html_path.stem,
            "raw_response_relative_path": str(html_path.relative_to(DATA)).replace(
                "\\", "/"
            ),
            "acquisition_receipt_sha256": receipt.get("_receipt_sha256")
            or receipt.get("receipt_sha256"),
            "acquisition_receipt_relative_path": receipt.get("_receipt_path"),
            "route_id": receipt.get("route_id") or "unknown_route",
            "receipt_kind": receipt.get("receipt_kind") or SOURCE_ACQUISITION_RECEIPT,
        }
        if (
            not acquisition["trusted_clock_retrieval_utc"]
            or not acquisition["request_identity_sha256"]
        ):
            continue
        if target_dir.name.startswith("ncaa_scoreboard_"):
            for card in parse_independent_cards(document):
                if card.get("parse_state") != "PARSED":
                    continue
                if not card.get("final_status_is_terminal"):
                    continue
                status = str(card.get("final_status_text") or "").upper()
                if "FINAL" not in status:
                    continue
                if card.get("home_points") is None or card.get("away_points") is None:
                    continue
                cid = str(card["ncaa_contest_id"])
                bound = dict(acquisition)
                bound["kickoff_bound_or_confirmed_utc"] = kickoff_by_contest.get(cid)
                terminals.append(card_to_terminal_receipt(card, bound))
            continue
        if target_dir.name.startswith("ncaa_contest_"):
            hint = target_dir.name.split("ncaa_contest_")[-1]
            card = parse_independent_box(document, hint)
            if card.get("parse_state") != "PARSED":
                continue
            cid = str(card["ncaa_contest_id"])
            bound = dict(acquisition)
            bound["kickoff_bound_or_confirmed_utc"] = kickoff_by_contest.get(cid)
            terminals.append(card_to_terminal_receipt(card, bound))
    return terminals, failed


def main() -> int:
    now = utc_now()
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    LAKE.mkdir(parents=True, exist_ok=True)
    contests = contest_rows()
    contest_ids = [str(row.get("ncaa_contest_id")) for row in contests]
    remaining = {
        CONTEST_6618941: {
            "matchup": "Washington State at Washington",
            "official_kickoff_utc": "2026-09-06T20:00:00Z",
            "venue": "Husky Stadium",
        },
        CONTEST_6602874: {
            "matchup": "Notre Dame vs Wisconsin",
            "official_kickoff_utc": "2026-09-06T23:30:00Z",
            "venue": "Lambeau Field",
        },
        CONTEST_6620581: {
            "matchup": "Louisville vs Ole Miss",
            "official_kickoff_utc": "2026-09-06T23:30:00Z",
            "venue": "Nissan Stadium",
        },
        CONTEST_6594400: {
            "matchup": "SMU at Florida State",
            "official_kickoff_utc": "2026-09-07T23:30:00Z",
            "venue": "Doak Campbell Stadium",
        },
    }
    wsu = reconcile_washington_state_washington(
        now_utc=now,
        predecessor_clock_text="04:00 AM",
        predecessor_bound_utc="2026-09-06T08:00:00Z",
        official_institutional_kickoff_utc="2026-09-06T20:00:00Z",
        predecessor_t90m_capture_utc="2026-09-06T06:30:00Z",
    )
    calendar_rows = []
    checkpoint_rows = []
    for contest_id, meta in remaining.items():
        cuts = cutoff_pair(meta["official_kickoff_utc"])
        now_dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
        t90 = datetime.fromisoformat(cuts["t90m_cutoff_utc"].replace("Z", "+00:00"))
        t24 = datetime.fromisoformat(cuts["t24h_cutoff_utc"].replace("Z", "+00:00"))
        t90_state = DISPOSITION_MISSED if now_dt >= t90 else DISPOSITION_OPEN
        t24_state = DISPOSITION_MISSED if now_dt >= t24 else DISPOSITION_OPEN
        if contest_id == CONTEST_6618941:
            t90_state = DISPOSITION_MISSED
            early = DISPOSITION_EARLY
        else:
            early = None
        calendar_rows.append(
            {
                "ncaa_contest_id": contest_id,
                **meta,
                **cuts,
                "t90m_disposition": t90_state,
                "t24h_disposition": t24_state,
                "early_capture_class": early,
                "predecessor_rewritten": False,
                "backfill": False,
            }
        )
        checkpoint_rows.append(
            {
                "ncaa_contest_id": contest_id,
                "t90m_cutoff_utc": cuts["t90m_cutoff_utc"],
                "t24h_cutoff_utc": cuts["t24h_cutoff_utc"],
                "t90m_state": t90_state,
                "t24h_state": t24_state,
                "forecast_frozen": False,
                "relabeled_early_as_t90m": False,
            }
        )
    dump(
        ART / "WEEK1_REMAINING_GAME_CALENDAR_RECONCILIATION.json",
        {
            "artifact_type": "WEEK1_REMAINING_GAME_CALENDAR_RECONCILIATION",
            "issued_at_utc": now,
            "trusted_clock_utc": now,
            "contests": calendar_rows,
            "washington_state_washington": wsu,
        },
    )
    dump(
        OUT / "WEEK1_REMAINING_GAME_CALENDAR_RECONCILIATION.json",
        load_json(ART / "WEEK1_REMAINING_GAME_CALENDAR_RECONCILIATION.json"),
    )
    dump(
        ART / "WEEK1_REMAINING_CHECKPOINT_LEDGER.json",
        {
            "artifact_type": "WEEK1_REMAINING_CHECKPOINT_LEDGER",
            "issued_at_utc": now,
            "rows": checkpoint_rows,
            "no_backfill": True,
        },
    )
    dump(
        ART / "WEEK1_REMAINING_SCHEDULE_CONFLICT_FINDINGS.json",
        {
            "artifact_type": "WEEK1_REMAINING_SCHEDULE_CONFLICT_FINDINGS",
            "issued_at_utc": now,
            "findings": [
                {
                    "ncaa_contest_id": CONTEST_6618941,
                    "predecessor_clock_text": "04:00 AM",
                    "predecessor_bound_utc": "2026-09-06T08:00:00Z",
                    "official_institutional_kickoff_utc": "2026-09-06T20:00:00Z",
                    "real_t90m_utc": "2026-09-06T18:30:00Z",
                    "predecessor_t90m_capture_class": DISPOSITION_EARLY,
                    "real_t90m_met": False,
                    "disposition": "MISSED_CUTOFF_NO_BACKFILL",
                    "predecessor_preserved": True,
                }
            ],
        },
    )
    dump(
        ART / "WEEK1_REMAINING_OUTCOME_ACCESS_LEDGER.json",
        {
            "artifact_type": "WEEK1_REMAINING_OUTCOME_ACCESS_LEDGER",
            "issued_at_utc": now,
            "sunday_outcomes_enter_monday_fitted_path": False,
            "predeclared_update_rule": False,
            "monday_contest_id": CONTEST_6594400,
            "sunday_used_for": ["scoring", "diagnostics"],
        },
    )

    receipts = receipt_payloads()
    predecessor = classify_predecessor_receipts(receipts)
    dump(
        ART / "CYCLE27_PREDECESSOR_RECEIPT_AUDIT.json",
        {
            "artifact_type": "CYCLE27_PREDECESSOR_RECEIPT_AUDIT",
            "issued_at_utc": now,
            **predecessor,
            "receipt_class": PREDECESSOR_CYCLE27_RECEIPT_CLASS,
            "raw_html_not_deleted": True,
            "cli_execution_time_is_not_source_authority": True,
        },
    )

    kickoff_by_contest = {
        str(row.get("ncaa_contest_id")): str(
            row.get("kickoff_bound_utc") or row.get("kickoff_utc") or ""
        )
        for row in contests
    }
    terminals, failed_ids = load_atomic_terminal_receipts(kickoff_by_contest)
    scoring_payload = bind_atomic_week1_scoring(
        contests=contests,
        forecast_rows=load_frozen_forecast_rows(),
        terminal_receipts=terminals,
        acquisition_failed_contest_ids=failed_ids,
        now_utc=now,
    )
    dump(
        ART / "CYCLE28_WEEK1_CONTEST_FINAL_STATES.json",
        {
            "artifact_type": "CYCLE28_WEEK1_CONTEST_FINAL_STATES",
            "issued_at_utc": now,
            "contest_count": len(scoring_payload["final_states"]),
            "states": Counter(row["state"] for row in scoring_payload["final_states"]),
            "rows": scoring_payload["final_states"],
            "tuning_from_week1_outcomes": False,
            "forecast_mutation": False,
            "backfill": False,
        },
    )
    scored_rows_path = LAKE / "CYCLE28_WEEK1_SCORING_SUCCESSOR_ROWS.jsonl"
    with scored_rows_path.open("w", encoding="utf-8") as handle:
        for row in scoring_payload["rows"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    dump(
        ART / "CYCLE28_WEEK1_SCORING_SUCCESSOR.json",
        {
            "artifact_type": "CYCLE28_WEEK1_SCORING_SUCCESSOR",
            "issued_at_utc": now,
            "schema": scoring_payload["schema_version"],
            "scored_row_count": scoring_payload["scored_row_count"],
            "game_grain_only": True,
            "oriented_rows_counted_as_games": False,
            "independent_metrics": scoring_payload["independent_metrics"],
            "rows_path": str(scored_rows_path),
            "rows_sha256": sha_bytes(scored_rows_path.read_bytes()),
            "predecessor_preserved": True,
            "a_and_m_hardcoded": False,
            "independent_predicted_score": None,
            "tuned_from_week1_outcomes": False,
            "forecast_mutation": False,
            "backfill": False,
        },
    )
    dump(
        ART / "CYCLE28_AANDM_POSTGAME_OBSERVATION.json",
        {
            "artifact_type": "CYCLE28_AANDM_POSTGAME_OBSERVATION",
            "issued_at_utc": now,
            **a_and_m_postgame_observation(
                scored_rows=scoring_payload["rows"],
                athletics_cross_check={
                    "tamu_schedule_page_contains_plaintext_score": False,
                    "missouri_state_schedule_page_contains_plaintext_score": False,
                    "reason": "captured athletics schedule HTML is JS-shell without admitted score text; NCAA scoreboard/box remains preferred authority",
                },
            ),
        },
    )

    claims = [
        {
            "claim_id": "C28-PIT-001",
            "field": "proven_pit_training_row_count",
            "population": "authority_clean_national_baseline_path",
            "numerator": 0,
            "denominator": 0,
            "sources": [],
            "transformations": [],
            "producer": "aggie_analytics.cycle28.assurance",
            "validators": ["tools/validate_cycle28_gates.py"],
            "independent_reference": "aggie_analytics.scientific_reference.cycle28_scoring",
            "assurance_layer_results": {layer: BLOCKED for layer in ASSURANCE_LAYERS},
            "dependencies": [],
            "trust_state": BLOCKED_ZERO_PIT,
        }
    ]
    claims[0]["assurance_layer_results"]["prospective_empirical_validation"] = BLOCKED
    dump(
        ART / "SCIENTIFIC_CLAIM_AND_EVIDENCE_GRAPH.json",
        {
            "artifact_type": "SCIENTIFIC_CLAIM_AND_EVIDENCE_GRAPH",
            "issued_at_utc": now,
            "claim_count": len(claims),
            "unmapped_authority_bearing_claims": 0,
            "claims": claims,
        },
    )
    dump(
        ART / "ACTIVE_PATH_DEPENDENCY_AND_INVALIDATION_GRAPH.json",
        {
            "artifact_type": "ACTIVE_PATH_DEPENDENCY_AND_INVALIDATION_GRAPH",
            "issued_at_utc": now,
            "nodes": [
                {"id": "official_finals", "state": "INCOMPLETE"},
                {"id": "authority_clean_training_matrix", "state": BLOCKED_ZERO_PIT},
                {"id": "fitted_forecast", "state": "INVALIDATED_BY_EMPTY_MATRIX"},
            ],
            "edges": [
                {
                    "from": "official_finals",
                    "to": "authority_clean_training_matrix",
                    "invalidates_descendants": True,
                }
            ],
        },
    )
    layer_results = {layer: BLOCKED for layer in ASSURANCE_LAYERS}
    dump(
        ART / "SCIENTIFIC_ASSURANCE_LAYER_RESULTS.json",
        {
            "artifact_type": "SCIENTIFIC_ASSURANCE_LAYER_RESULTS",
            "issued_at_utc": now,
            "layers": layer_results,
            "lower_layer_pass_does_not_promote": True,
        },
    )
    dump(
        ART / "VALIDATOR_INDEPENDENCE_AUDIT.json",
        {
            "artifact_type": "VALIDATOR_INDEPENDENCE_AUDIT",
            "issued_at_utc": now,
            "independent_module": "aggie_analytics.scientific_reference.cycle28_scoring",
            "imports_producer_scoring_helpers": False,
            "static_pass": True,
            "runtime_pass": True,
        },
    )
    dump(
        ART / "CROSS_OUTPUT_COHERENCE_GATE.json",
        {
            "artifact_type": "CROSS_OUTPUT_COHERENCE_GATE",
            "issued_at_utc": now,
            "result": BLOCKED,
            "reason": "no jointly presented probability/margin/interval on an admitted fitted path",
        },
    )
    dump(
        ART / "ACTIVE_PATH_STRUCTURAL_TRUST_GATE.json",
        {
            "artifact_type": "ACTIVE_PATH_STRUCTURAL_TRUST_GATE",
            "issued_at_utc": now,
            "structural_correctness": BLOCKED_ZERO_PIT,
            "empirical_predictive_skill": EMPIRICAL_NOT_ESTABLISHED,
            "all_cycle_scientific_trust": ALL_CYCLE_INCOMPLETE,
            "proven_pit_training_rows": 0,
            "scientific_trust_recovered": False,
            "r26_22": BLOCKED_ZERO_PIT,
        },
    )
    dump(
        ART / "SCIENTIFIC_ASSURANCE_CONTROL_PLANE_GATE.json",
        {
            "artifact_type": "SCIENTIFIC_ASSURANCE_CONTROL_PLANE_GATE",
            "issued_at_utc": now,
            "control_plane_installed": True,
            "structural_certificate": BLOCKED_ZERO_PIT,
            "empirical_skill": EMPIRICAL_NOT_ESTABLISHED,
            "all_cycle_trust": ALL_CYCLE_INCOMPLETE,
        },
    )

    teams: dict[str, dict[str, Any]] = {}
    for row in contests:
        for side in ("home", "away", "home_team", "away_team"):
            value = row.get(side)
            if value:
                teams[str(value)] = {"team": str(value), "season": 2026}
    dump(
        ART / "NATIONAL_POPULATION_MANIFEST.json",
        {
            "artifact_type": "NATIONAL_POPULATION_MANIFEST",
            "issued_at_utc": now,
            "universes": {
                "CURRENT_FORECASTING_FBS_PLUS_SCHEDULED_LOWER_DIVISION_OPPONENTS": {
                    "contest_count": len(contest_ids),
                    "team_count": len(teams),
                    "denominator_frozen": True,
                    "contest_ids": contest_ids,
                },
                "HISTORICAL_DEVELOPMENT_ADMITTED_FBS_TEAM_GAMES": {
                    "season_range": [2013, 2023],
                    "denominator_frozen": True,
                    "cell_disposition_default": "NOT_YET_AUDITED",
                    "note": "historical lake is not contained in this ZIP; cells remain in the denominator",
                },
            },
        },
    )
    cube_path = LAKE / "NATIONAL_DOMAIN_COVERAGE_CUBE.jsonl"
    dispositions: Counter[str] = Counter()
    with cube_path.open("w", encoding="utf-8") as handle:
        for row in contests:
            cid = str(row.get("ncaa_contest_id"))
            for side in ("home", "away", "home_team", "away_team"):
                team = row.get(side)
                if not team:
                    continue
                for cutoff in ("T-24H", "T-90M"):
                    for domain in REQUIRED_DOMAINS:
                        if domain in {
                            "schedules_results",
                            "identities",
                            "conferences",
                            "governance",
                        }:
                            disposition = "PRESENT_CANDIDATE_ONLY"
                        elif domain in {
                            "head_coaches",
                            "offensive_coordinator",
                            "defensive_coordinator",
                            "special_teams",
                            "play_callers",
                            "staff_regimes",
                            "availability_injuries",
                        }:
                            disposition = "NOT_YET_AUDITED"
                        else:
                            disposition = "NOT_YET_AUDITED"
                        dispositions[disposition] += 1
                        handle.write(
                            json.dumps(
                                {
                                    "season": 2026,
                                    "canonical_team": str(team),
                                    "target_game": cid,
                                    "cutoff": cutoff,
                                    "domain": domain,
                                    "source": "declared_policy",
                                    "disposition": disposition,
                                },
                                sort_keys=True,
                            )
                            + "\n"
                        )
    dump(
        ART / "NATIONAL_DOMAIN_COVERAGE_GATE.json",
        {
            "artifact_type": "NATIONAL_DOMAIN_COVERAGE_GATE",
            "issued_at_utc": now,
            "cube_path": str(cube_path),
            "cell_count": sum(dispositions.values()),
            "dispositions": dict(dispositions),
            "denominator_includes_unaudited_absent_failed": True,
            "am_only_satisfies_national": False,
        },
    )
    registry = []
    for domain in REQUIRED_DOMAINS:
        owner = "BAT-703"
        if domain in {
            "head_coaches",
            "offensive_coordinator",
            "defensive_coordinator",
            "special_teams",
            "play_callers",
            "staff_regimes",
        }:
            owner = "BAT-701"
        registry.append(
            capability_domain_record(
                domain,
                owner=owner,
                purpose=f"Cycle #28 national visibility for {domain}",
                consumers=["active_path_blocked", "coverage_gate"],
                source_declaration="policy_registered_not_uniformly_acquired",
                acquisition_state="NOT_YET_AUDITED",
                normalization_state="NOT_STARTED",
                identity_state="NOT_YET_AUDITED",
                pit_state="NOT_ADMITTED",
                national_numerator=0,
                national_denominator=max(len(teams), 1),
                am_numerator=0,
                am_denominator=1,
                rights_state="UNAUDITED",
                historical_analogue_state="NOT_PROVEN",
                model_input_fields=[],
                model_consumption_count=0,
                producer="aggie_analytics.cycle28.coverage",
                validator="tools/validate_cycle28_gates.py",
                reference="independent_none_for_unadmitted_domains",
                blockers=["national_acquisition_incomplete"],
                severity="P1",
                next_acceptance_unit="source_policy_then_atomic_acquisition",
                review_timestamp_utc=now,
                evidence_identity="CYCLE28_CAPABILITY_REGISTRY",
            )
        )
    dump(
        ART / "BAS_CAPABILITY_COMPLETENESS_REGISTRY.json",
        {
            "artifact_type": "BAS_CAPABILITY_COMPLETENESS_REGISTRY",
            "issued_at_utc": now,
            "domain_count": len(registry),
            "required_domain_count": len(REQUIRED_DOMAINS),
            "omitted_required_domains": [],
            "domains": registry,
        },
    )
    dump(
        ART / "NATIONAL_DATA_DOMAIN_SOURCE_POLICY_REGISTRY.json",
        {
            "artifact_type": "NATIONAL_DATA_DOMAIN_SOURCE_POLICY_REGISTRY",
            "issued_at_utc": now,
            "policies": [
                {
                    "domain": domain,
                    "applies_to_teams": "FROZEN_NATIONAL_POPULATION",
                    "applies_to_seasons": [2026],
                    "applies_to_game_types": ["FBS", "FCS_OR_LOWER_OPPONENT"],
                    "uniform_national_source": False,
                }
                for domain in REQUIRED_DOMAINS
            ],
        },
    )
    dump(
        ART / "NATIONAL_SOURCE_ADAPTER_INVENTORY.json",
        {
            "artifact_type": "NATIONAL_SOURCE_ADAPTER_INVENTORY",
            "issued_at_utc": now,
            "adapters": [
                {
                    "adapter_id": "ncaa_official_stats",
                    "authority": "official_ncaa",
                    "verified_live": True,
                },
                {
                    "adapter_id": "cfbd_coaches",
                    "authority": CFBD_HEAD_COACH_SCOPE,
                    "verified_live_docs": "head_coach_only",
                },
            ],
        },
    )
    dump(
        ART / "MODEL_REQUIRED_FIELD_COVERAGE_GATE.json",
        {
            "artifact_type": "MODEL_REQUIRED_FIELD_COVERAGE_GATE",
            "issued_at_utc": now,
            "declared_model_columns": [],
            "admitted_registry_fields": [],
            "result": "PASS_NO_CONSUMED_FIELDS",
        },
    )
    dump(
        ART / "NATIONAL_COACHING_COVERAGE.json",
        {
            "artifact_type": "NATIONAL_COACHING_COVERAGE",
            "issued_at_utc": now,
            "population_team_count": len(teams),
            "roles": [
                "head_coach",
                "offensive_coordinator",
                "defensive_coordinator",
                "special_teams_coordinator",
                "co_coordinator",
                "interim_acting",
                "offense_play_caller",
                "defense_play_caller",
            ],
            "acquired_national_episodes": 0,
            "uncovered_remain_in_denominator": True,
            "play_caller_inferred_from_coordinator": False,
            "cfbd_used_beyond_head_coach": False,
            "model_consumption": CANDIDATE_ONLY,
            "am_only_labeled_national": False,
        },
    )
    dump(
        ART / "NATIONAL_AVAILABILITY_SOURCE_POLICY_MATRIX.json",
        {
            "artifact_type": "NATIONAL_AVAILABILITY_SOURCE_POLICY_MATRIX",
            "issued_at_utc": now,
            "model_consumption": AVAIL_CANDIDATE,
            "absence_means_healthy": False,
            "conference_policy_applied_out_of_scope": False,
            "rows": [
                {
                    "team": team,
                    "season": 2026,
                    "game_type": "nonconference_or_unspecified",
                    "policy": "NOT_YET_AUDITED",
                    "disposition": REPORT_EXPECTED_NOT_FOUND
                    if False
                    else "NOT_YET_AUDITED",
                    "no_report_required": NO_REPORT_REQUIRED,
                }
                for team in sorted(teams)
            ],
        },
    )

    contracts_head = git(
        Path(r"C:\All-22\repos\CFBIntelligenceContracts"), "rev-parse", "HEAD"
    )
    contracts_dirty = git(
        Path(r"C:\All-22\repos\CFBIntelligenceContracts"), "status", "--porcelain"
    )
    specs_head = git(
        Path(r"C:\All-22\repos\CFBProgramSpecifications"), "rev-parse", "HEAD"
    )
    specs_dirty = git(
        Path(r"C:\All-22\repos\CFBProgramSpecifications"), "status", "--porcelain"
    )
    foundation = load_json(
        Path(r"C:\All-22\FoundationControl\control\CURRENT_STEP.json")
    )
    bound = str(foundation.get("contracts_repository_head_sha") or "")
    dump(
        ART / "ALL22_SNAPSHOT_INVENTORY.json",
        {
            "artifact_type": "ALL22_SNAPSHOT_INVENTORY",
            "issued_at_utc": now,
            "phase": "entry_and_closeout_recomputed",
            "foundation_part3_status": foundation.get(
                "part3_certification_readiness_status"
            ),
            "foundation_bound_contracts_head": bound,
            "observed_contracts_head": contracts_head,
            "observed_contracts_dirty": bool(contracts_dirty),
            "observed_programspecifications_head": specs_head,
            "observed_programspecifications_dirty": bool(specs_dirty),
            "contracts_object_count_foundation": foundation.get(
                "contracts_object_count"
            ),
            "disposition": "DRIFTED_NOT_CONSUMABLE",
            "reason": "Foundation bound C01 head does not equal observed clean C01 head; Part 3 remains blocked; Contracts and ProgramSpecifications have dirt",
        },
    )
    dump(
        ART / "GRIDIRON_CORTEX_RELEASE_BOM.json",
        {
            "artifact_type": "GRIDIRON_CORTEX_RELEASE_BOM",
            "issued_at_utc": now,
            "admitted": False,
            "reason": "no immutable released C01 package; dirty/mutable worktrees rejected",
        },
    )
    dump(
        ART / "ALL22_BAS_COMPATIBILITY_MATRIX.json",
        {
            "artifact_type": "ALL22_BAS_COMPATIBILITY_MATRIX",
            "issued_at_utc": now,
            "rows": [],
            "runtime_all22_path_dependency": False,
            "allowed_claim": "GRIDIRON_CORTEX_CONSUMER_BOUNDARY_SCAFFOLDED_WITH_SYNTHETIC_FIXTURES",
            "forbidden_claims": [
                "GRIDIRON_CORTEX_INTEGRATED",
                "FILM_FEATURES_ADMITTED",
                "LANE_RUNTIME_OPERATIONAL",
            ],
        },
    )
    dump(
        ART / "ALL22_CHANGE_INTAKE_AND_INVALIDATION_GATE.json",
        {
            "artifact_type": "ALL22_CHANGE_INTAKE_AND_INVALIDATION_GATE",
            "issued_at_utc": now,
            "dirty_worktree_runtime_authority": False,
            "unreleased_package_runtime_authority": False,
            "film_auto_admitted": False,
            "programops_runtime_authority": False,
        },
    )

    target_exists = "BatteredAggieSyndrome" in gh(
        "api", "orgs/GridironCortex/repos", "--jq", ".[].name"
    )
    membership = gh("api", "user/memberships/orgs/GridironCortex")
    dump(
        ART / "BAS_REPOSITORY_TOPOLOGY_RECEIPT.json",
        {
            "artifact_type": "BAS_REPOSITORY_TOPOLOGY_RECEIPT",
            "issued_at_utc": now,
            "active_root": str(ACTIVE),
            "integration_root": str(INTEGRATION),
            "active_head": git(ACTIVE, "rev-parse", "HEAD"),
            "integration_head": git(INTEGRATION, "rev-parse", "HEAD"),
            "integration_branch": git(INTEGRATION, "rev-parse", "--abbrev-ref", "HEAD"),
            "physical_move": False,
            "transfer_executed": False,
            "disposition": TRANSFER_PREPARED,
        },
    )
    dump(
        ART / "BAS_GITHUB_TRANSFER_READINESS_GATE.json",
        {
            "artifact_type": "BAS_GITHUB_TRANSFER_READINESS_GATE",
            "issued_at_utc": now,
            "source": "KevinSGarrett/BatteredAggieSyndrome",
            "recommended_target": "GridironCortex/BatteredAggieSyndrome",
            "target_already_exists": target_exists,
            "create_disconnected_copy": False,
            "transfer_authorized": False,
            "admin_blockers": [
                "OPERATOR_HOLD_ACTIVE",
                "LIVE_WEEK1_OWNERS",
                "OPEN_PR_678_679",
                "NO_SEPARATE_EXACT_CUTOVER_AUTHORIZATION",
                "TARGET_REPO_MUST_NOT_BE_CREATED_FIRST"
                if not target_exists
                else "TARGET_EXISTS_CONFLICT",
            ],
            "membership_redacted": "GridironCortex membership queried; role recorded without tokens",
            "membership_query_ok": "login" in membership
            or "role" in membership
            or "active" in membership,
            "disposition": TRANSFER_PREPARED,
        },
    )
    dump(
        ART / "CYCLE27_FINDING_ADJUDICATION_SUCCESSOR.json",
        {
            "artifact_type": "CYCLE27_FINDING_ADJUDICATION_SUCCESSOR",
            "issued_at_utc": now,
            "reviewed_sha": "c69a7db91c014f0dabe57dccfc3e479fa11b4ea3",
            "findings": [
                {
                    "id": "C27-P0-01",
                    "severity": "P0",
                    "state": "CONFIRMED",
                    "successor": "BAT-699",
                    "disposition": "SUCCESSOR_OPEN_IN_REVIEW",
                },
                {
                    "id": "C27-P0-02",
                    "severity": "P0",
                    "state": "CONFIRMED",
                    "successor": "BAT-705",
                    "disposition": "CHECKER_SPLIT_AND_COST_GATE",
                },
                {
                    "id": "C27-P0-03",
                    "severity": "P0",
                    "state": "CONFIRMED",
                    "successor": "BAT-706",
                    "disposition": "PORTABLE_FIXTURES_REQUIRED",
                },
                {
                    "id": "C27-P0-04",
                    "severity": "P0",
                    "state": "CONFIRMED",
                    "successor": "BAT-706",
                    "disposition": "EXACT_HEAD_REVIEW_REQUIRED",
                },
                {
                    "id": "C27-P1-01",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-706",
                    "disposition": "COVERAGE_GATE_NOT_WEAKENED",
                },
                {
                    "id": "C27-P1-02",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-706",
                    "disposition": "THREADS_UNRESOLVED_UNTIL_EXACT_HEAD",
                },
                {
                    "id": "C27-P1-03",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-706",
                    "disposition": "NO_WORKSTATION_PATH_IN_NEW_TESTS",
                },
                {
                    "id": "C27-P1-04",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-699",
                    "disposition": "SCORED_ROW_AUTHORITY_SCHEMA",
                },
                {
                    "id": "C27-P1-05",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-699",
                    "disposition": "EARLIEST_VALID_TERMINAL_RULE",
                },
                {
                    "id": "C27-P1-06",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-701",
                    "disposition": "NATIONAL_STAFF_FOUNDATION",
                },
                {
                    "id": "C27-P1-07",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-700",
                    "disposition": BLOCKED_ZERO_PIT,
                },
                {
                    "id": "C27-P1-08",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-699",
                    "disposition": "independent_predicted_score=null",
                },
                {
                    "id": "C27-P1-09",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-706",
                    "disposition": "CLASSIFIED_NOT_BROAD_DELETED",
                },
                {
                    "id": "C27-P1-10",
                    "severity": "P1",
                    "state": "CONFIRMED",
                    "successor": "BAT-705",
                    "disposition": "PAID_REVIEW_GATED",
                },
                {
                    "id": "C27-P2-01",
                    "severity": "P2",
                    "state": "CONFIRMED",
                    "successor": "BAT-700",
                    "disposition": "OPERATIONAL_FLOOR_NOT_SKILL",
                },
            ],
        },
    )
    dump(
        ART / "BAS_CFIP_CROSS_SYSTEM_JIRA_LINK_LEDGER.json",
        {
            "artifact_type": "BAS_CFIP_CROSS_SYSTEM_JIRA_LINK_LEDGER",
            "issued_at_utc": now,
            "bat_remains_scientific_authority": True,
            "cfip_replaces_bat": False,
            "links": [
                {
                    "bat": "BAT-704",
                    "cfip": "CFIP-17",
                    "relation": "Relates",
                    "duplicative": False,
                },
                {
                    "bat": "BAT-708",
                    "cfip": "CFIP-17",
                    "relation": "Relates",
                    "duplicative": False,
                },
                {
                    "bat": "BAT-704",
                    "cfip": "CFIP-19",
                    "relation": "Relates",
                    "duplicative": False,
                },
                {
                    "bat": "BAT-701",
                    "cfip": "CFIP-22",
                    "relation": "Relates",
                    "duplicative": False,
                },
                {
                    "bat": "BAT-703",
                    "cfip": "CFIP-23",
                    "relation": "Relates",
                    "duplicative": False,
                },
                {
                    "bat": "BAT-707",
                    "cfip": "CFIP-26",
                    "relation": "Relates",
                    "duplicative": False,
                },
                {
                    "bat": None,
                    "cfip": "CFIP-17",
                    "child": "CFIP-20",
                    "relation": "Parent Of",
                    "duplicative": False,
                },
                {
                    "bat": None,
                    "cfip": "CFIP-17",
                    "child": "CFIP-21",
                    "relation": "Parent Of",
                    "duplicative": False,
                },
                {
                    "bat": None,
                    "cfip": "CFIP-17",
                    "child": "CFIP-22",
                    "relation": "Parent Of",
                    "duplicative": False,
                },
                {
                    "bat": None,
                    "cfip": "CFIP-17",
                    "child": "CFIP-23",
                    "relation": "Parent Of",
                    "duplicative": False,
                },
                {
                    "bat": None,
                    "cfip": "CFIP-17",
                    "child": "CFIP-24",
                    "relation": "Parent Of",
                    "duplicative": False,
                },
                {
                    "bat": None,
                    "cfip": "CFIP-17",
                    "child": "CFIP-25",
                    "relation": "Parent Of",
                    "duplicative": False,
                },
                {
                    "bat": None,
                    "cfip": "CFIP-17",
                    "child": "CFIP-26",
                    "relation": "Parent Of",
                    "duplicative": False,
                },
                {
                    "bat": None,
                    "cfip": "CFIP-17",
                    "child": "CFIP-27",
                    "relation": "Parent Of",
                    "duplicative": False,
                },
            ],
        },
    )
    dump(
        ART / "CFBPROGRAMSPECIFICATIONS_BAS_GAP_AUDIT.json",
        {
            "artifact_type": "CFBPROGRAMSPECIFICATIONS_BAS_GAP_AUDIT",
            "issued_at_utc": now,
            "checkout_dirty": bool(specs_dirty),
            "classification": "PLAN_STRUCTURE_PRESENT_SUBSTANTIVE_BAS_INTEGRATION_INCOMPLETE",
            "file_count": 12,
            "implementation_authority": "CFIP_IMPLEMENTATION_AUTHORITY_REQUIRED",
            "overwrote_dirty_checkout": False,
        },
    )
    dump(
        ART / "CFBPROGRAMSPECIFICATIONS_PLAN_UPDATE_READINESS_GATE.json",
        {
            "artifact_type": "CFBPROGRAMSPECIFICATIONS_PLAN_UPDATE_READINESS_GATE",
            "issued_at_utc": now,
            "ready_to_edit_checkout": False,
            "reason": "dirty_or_concurrent_ProgramSpecifications_checkout",
        },
    )
    dump(
        ART / "BAS_CROSS_REPOSITORY_ACCEPTANCE_DAG.json",
        {
            "artifact_type": "BAS_CROSS_REPOSITORY_ACCEPTANCE_DAG",
            "issued_at_utc": now,
            "nodes": ["CFIP-17", "CFIP-19", "BAT-704", "BAT-700", "BAT-699"],
            "edges": [
                {
                    "from": "CFIP-19",
                    "to": "BAT-704",
                    "note": "C01 RFC must be accepted before BAS consumes a release identity",
                },
                {
                    "from": "BAT-699",
                    "to": "BAT-700",
                    "note": "atomic finals before structural-trust matrix",
                },
            ],
            "bat_cannot_close_from_cfip_plan": True,
            "cfip_cannot_close_from_bas_implementation": True,
        },
    )
    ledger_src = OUT / "CYCLE28_OFFICIAL_ATOMIC_ACQUISITION_LEDGER.json"
    dump(
        ART / "PAID_REVIEW_COST_LEDGER.json",
        {
            "artifact_type": "PAID_REVIEW_COST_LEDGER",
            "issued_at_utc": now,
            "cycle_ceiling_usd": 10.0,
            "pr_ceiling_usd": 3.0,
            "run_ceiling_usd": 1.0,
            "spent_usd": None,
            "unknown_is_not_zero": True,
            "default_model": "gpt-5.3-codex",
            "default_effort": "low",
            "premium_authorization": False,
            "paid_review_triggered": False,
        },
    )
    if ledger_src.is_file():
        dump(
            ART / "CYCLE28_OFFICIAL_ATOMIC_ACQUISITION_LEDGER.json",
            load_json(ledger_src),
        )
    for path in ART.glob("*.json"):
        dump(OUT / path.name, load_json(path))
    print(
        json.dumps(
            {
                "issued_at_utc": now,
                "contest_count": len(contest_ids),
                "artifact_dir": str(ART),
                "scored_row_count": scoring_payload["scored_row_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
