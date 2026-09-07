"""Materialize Cycle #29 control-plane artifacts.

Does not claim empirical skill, a champion, BAS, or all-cycle trust recovery.
Does not merge scientific PRs or mark scientific issues Done.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# Tool scripts must import the local package after PATH setup.
# ruff: noqa: E402

from aggie_analytics.cycle29.claims import (
    discover_authority_claims,
    inventory_claims,
    kernel_closure_claims,
)
from aggie_analytics.cycle29.coaching import (
    extract_registry_identities,
    hc_oc_dc_matrix,
    historical_lattice,
    model_admission_gate,
    position_role_contract,
    reconcile_predecessor_observations,
)
from aggie_analytics.cycle29.dependency import static_import_graph
from aggie_analytics.cycle29.domains import canonical_catalog, crosswalk, grain_contract
from aggie_analytics.cycle29.findings import successor_ledger
from aggie_analytics.cycle29.forecast import prove_issued_before_cutoff, rehash_payload
from aggie_analytics.cycle29.hashing import sha256_file, sha256_json
from aggie_analytics.cycle29.pit_kernel import (
    build_game_grain_kernel,
    kernel_trust_gate,
    predecessor_reconciliation,
)
from aggie_analytics.cycle29.populations import (
    classify_predecessor_games,
    entity_authority_successor,
    fcs_subset_from_parent,
    historical_scope_contract,
    tamu_specialization_contract,
    week1_slice_from_contests,
)
from aggie_analytics.scientific_reference.cycle29.pit import (
    compare_producer_rows,
    reconstruct_game_features,
)

ART = ROOT / "artifacts" / "scientific_integrity" / "cycle29"
EXT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle29_work\outputs")
DATA = Path(r"C:\BatteredAggieSyndrome.data")
FORECAST_ROWS = (
    DATA
    / "canonical"
    / "week1_2026_game_grain_national_forecast_successor"
    / "sha256"
    / "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
    / "week1_2026_game_grain_forecast_rows.jsonl"
)
FORECAST_SHA = "7015c32d0041ecb2d3938139c00e3742321d8bd527aa9c76a8508d630e611b16"
PEOPLE_CSV = (
    DATA
    / "canonical"
    / "BAT-388"
    / "sha256"
    / "0ab6acafbe350a4958a5fca1c02a9c51463ab8a93ecc173a57b9fd925bf2198d"
    / "canonical_people_registry.csv"
)
WEEK1_STATES = (
    ROOT
    / "artifacts"
    / "scientific_integrity"
    / "cycle28"
    / "CYCLE28_WEEK1_CONTEST_FINAL_STATES.json"
)
AS_OF = "2026-09-07T16:00:00Z"
ROLE_FAMILIES = (
    "head_coach",
    "offensive_coordinator",
    "defensive_coordinator",
    "special_teams_coordinator",
    "quarterbacks",
    "running_backs",
    "wide_receivers",
    "tight_ends",
    "offensive_line",
    "defensive_line",
    "linebackers",
    "defensive_backs",
    "safeties",
    "cornerbacks",
    "nickels",
    "kickers_punters",
    "strength_conditioning",
    "analyst_support",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_bytes(body.encode("utf-8"))
    return sha256_file(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks = [
        json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows
    ]
    path.write_bytes("".join(chunks).encode("utf-8"))
    return sha256_file(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_kernel_games() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    games = [
        {
            "canonical_game_id": "GAME:A",
            "home_canonical_team_id": "TEAM:1",
            "away_canonical_team_id": "TEAM:2",
            "season": 2018,
            "start_date_utc_text": "2018-09-01T19:00:00Z",
        },
        {
            "canonical_game_id": "GAME:B",
            "home_canonical_team_id": "TEAM:1",
            "away_canonical_team_id": "TEAM:3",
            "season": 2018,
            "start_date_utc_text": "2018-09-08T19:00:00Z",
        },
        {
            "canonical_game_id": "GAME:C",
            "home_canonical_team_id": "TEAM:2",
            "away_canonical_team_id": "TEAM:3",
            "season": 2019,
            "start_date_utc_text": "2019-09-07T19:00:00Z",
        },
    ]
    outcomes = [
        {
            "canonical_game_id": "GAME:A",
            "canonical_team_id": "TEAM:1",
            "label_win": True,
            "points_for": 31,
            "points_against": 10,
            "margin": 21,
            "season": 2018,
        },
        {
            "canonical_game_id": "GAME:A",
            "canonical_team_id": "TEAM:2",
            "label_win": False,
            "points_for": 10,
            "points_against": 31,
            "margin": -21,
            "season": 2018,
        },
        {
            "canonical_game_id": "GAME:B",
            "canonical_team_id": "TEAM:1",
            "label_win": True,
            "points_for": 24,
            "points_against": 17,
            "margin": 7,
            "season": 2018,
        },
        {
            "canonical_game_id": "GAME:B",
            "canonical_team_id": "TEAM:3",
            "label_win": False,
            "points_for": 17,
            "points_against": 24,
            "margin": -7,
            "season": 2018,
        },
        {
            "canonical_game_id": "GAME:C",
            "canonical_team_id": "TEAM:2",
            "label_win": True,
            "points_for": 20,
            "points_against": 13,
            "margin": 7,
            "season": 2019,
        },
        {
            "canonical_game_id": "GAME:C",
            "canonical_team_id": "TEAM:3",
            "label_win": False,
            "points_for": 13,
            "points_against": 20,
            "margin": -7,
            "season": 2019,
        },
    ]
    return games, outcomes


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=str(ROOT), text=True, encoding="utf-8"
    ).strip()


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    EXT.mkdir(parents=True, exist_ok=True)
    issued = utc_now()
    hashes: dict[str, str] = {}

    contests = load_json(WEEK1_STATES).get("rows", [])
    week1 = week1_slice_from_contests(contests)
    hashes["WEEK1_2026_PROGRAM_SLICE.json"] = write_json(
        ART / "WEEK1_2026_PROGRAM_SLICE.json", week1
    )
    w = int(week1["distinct_canonical_program_count_W"])

    scope = historical_scope_contract()
    hashes["HISTORICAL_NATIONAL_PROGRAM_SEASON_SCOPE_CONTRACT.json"] = write_json(
        ART / "HISTORICAL_NATIONAL_PROGRAM_SEASON_SCOPE_CONTRACT.json", scope
    )
    expected_ps = [
        {
            "season": year,
            "era": (
                "NCAA_UNIVERSITY_DIVISION_PRIMARY"
                if year <= 1972
                else "UNSPLIT_DIVISION_I"
                if year <= 1977
                else "DIVISION_I_A_PLUS_DIVISION_I_AA"
                if year <= 2005
                else "FBS_PLUS_FCS"
            ),
            "enumeration_state": "BLOCKED_INDEPENDENT_ANNUAL_MEMBERSHIP_NOT_ENUMERATED",
            "program_id": None,
        }
        for year in range(1963, 2027)
    ]
    hashes["HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.jsonl"] = (
        write_jsonl(
            EXT / "HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.jsonl",
            expected_ps,
        )
    )
    hashes["HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.jsonl.gitstub"] = (
        write_json(
            ART
            / "HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.manifest.json",
            {
                "external_path": "ops/cycle29_work/outputs/HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.jsonl",
                "sha256": hashes[
                    "HISTORICAL_NATIONAL_PROGRAM_SEASON_EXPECTED_POPULATION.jsonl"
                ],
                "row_count": len(expected_ps),
                "enumeration_state": "BLOCKED_INDEPENDENT_ANNUAL_MEMBERSHIP_NOT_ENUMERATED",
            },
        )
    )

    current_pop = {
        "artifact_type": "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION",
        "as_of_utc": AS_OF,
        "enumeration_state": "BLOCKED_INDEPENDENT_MEMBERSHIP_EVIDENCE_UNAVAILABLE",
        "program_count_N": None,
        "is_week1_slice": False,
        "week1_cannot_replace_current": True,
        "programs": [],
        "identity": sha256_json({"as_of_utc": AS_OF, "state": "BLOCKED"}),
    }
    hashes["CURRENT_2026_DIVISION_I_PROGRAM_POPULATION.json"] = write_json(
        ART / "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION.json", current_pop
    )
    recon = {
        "artifact_type": "CURRENT_2026_PROGRAM_POPULATION_RECONCILIATION",
        "as_of_utc": AS_OF,
        "historical_2026_slice_identity": None,
        "current_population_identity": current_pop["identity"],
        "exact_equality": False,
        "reason": "BOTH_SIDES_BLOCKED_MEMBERSHIP_EVIDENCE",
        "week1_substitution_rejected": True,
    }
    hashes["CURRENT_2026_PROGRAM_POPULATION_RECONCILIATION.json"] = write_json(
        ART / "CURRENT_2026_PROGRAM_POPULATION_RECONCILIATION.json", recon
    )
    tamu = tamu_specialization_contract(
        current_pop["identity"], scope.get("artifact_type", "")
    )
    hashes["TAMU_SPECIALIZATION_POPULATION_CONTRACT.json"] = write_json(
        ART / "TAMU_SPECIALIZATION_POPULATION_CONTRACT.json", tamu
    )
    tamu_cells = [
        {
            "cell_id": "tamu-program-season",
            "grain": "program-season",
            "parent_population_identity": current_pop["identity"],
            "program_id": tamu["canonical_program_id"],
            "season": year,
        }
        for year in range(1963, 2027)
    ]
    hashes["TAMU_SPECIALIZATION_EXPECTED_OPPORTUNITY_CELLS.jsonl"] = write_jsonl(
        EXT / "TAMU_SPECIALIZATION_EXPECTED_OPPORTUNITY_CELLS.jsonl", tamu_cells
    )
    hashes["WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json"] = write_json(
        ART / "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json",
        entity_authority_successor(),
    )
    hashes["NATIONAL_PROGRAM_IDENTITY_CROSSWALK.json"] = write_json(
        ART / "NATIONAL_PROGRAM_IDENTITY_CROSSWALK.json",
        {
            "artifact_type": "NATIONAL_PROGRAM_IDENTITY_CROSSWALK",
            "display_names_are_not_canonical": True,
            "provider_aliases_preserved_separately": True,
            "week1_display_to_placeholder": week1["programs"][:10],
        },
    )

    games_cov = classify_predecessor_games(
        normalized_count=46953, entity_count=46960, fcs_to_fcs=0
    )
    hashes["HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json"] = write_json(
        ART / "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json", games_cov
    )
    parent_games = [
        {
            "season": 2020,
            "home_id": "P1",
            "away_id": "P2",
            "date": "2020-09-05",
            "home_class": "FBS",
            "away_class": "FCS",
            "disposition": "PLAYED",
        },
        {
            "season": 2020,
            "home_id": "P3",
            "away_id": "P4",
            "date": "2020-09-05",
            "home_class": "FCS",
            "away_class": "FCS",
            "disposition": "PLAYED",
        },
        {
            "season": 1970,
            "home_id": "P5",
            "away_id": "P6",
            "date": "1970-09-12",
            "home_class": "UNIVERSITY_DIVISION",
            "away_class": "UNIVERSITY_DIVISION",
            "disposition": "PLAYED",
        },
        {
            "season": 2020,
            "home_id": "P1",
            "away_id": "NON_DI",
            "date": "2020-09-12",
            "home_class": "FBS",
            "away_class": "NON_DIVISION_I",
            "disposition": "PLAYED",
        },
    ]
    parent_identity = sha256_json(parent_games)
    hashes["HISTORICAL_EXPECTED_GAME_POPULATION.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_EXPECTED_GAME_POPULATION.jsonl",
        [{**row, "parent_identity": parent_identity} for row in parent_games],
    )
    filter_id = sha256_json({"predicate": "1978plus_any_iaa_or_fcs"})
    fcs = fcs_subset_from_parent(
        parent_games,
        parent_identity=parent_identity,
        filter_contract_identity=filter_id,
    )
    hashes["HISTORICAL_FCS_EXPECTED_GAME_POPULATION.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_FCS_EXPECTED_GAME_POPULATION.jsonl",
        [
            {
                **row,
                "parent_identity": parent_identity,
                "filter_contract_identity": filter_id,
            }
            for row in fcs["rows"]
        ],
    )
    hashes["HISTORICAL_GAME_SOURCE_OBSERVATION_RECONCILIATION.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_GAME_SOURCE_OBSERVATION_RECONCILIATION.jsonl",
        [
            {
                "parent_contest": "P3-P4-2020-09-05",
                "source": "fixture",
                "duplicate_of_parent": True,
            }
        ],
    )
    hashes["HISTORICAL_CLASSIFICATION_EPISODES.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_CLASSIFICATION_EPISODES.jsonl",
        [
            {
                "program_id": "P3",
                "season": 2020,
                "classification": "FCS",
                "authority": "ERA_CONTRACT_2006_2026",
            },
            {
                "program_id": "P5",
                "season": 1970,
                "classification": "UNIVERSITY_DIVISION",
                "authority": "ERA_CONTRACT_1963_1972",
            },
        ],
    )
    hashes["SOURCE_ROUTE_COVERAGE_AND_RIGHTS_MATRIX.json"] = write_json(
        ART / "SOURCE_ROUTE_COVERAGE_AND_RIGHTS_MATRIX.json",
        {
            "cfbd_games_classification_fbs": "NUMERATOR_ONLY",
            "fcs_v_fcs_acquisition": "NOT_PERFORMED_RIGHTS_OR_SOURCE_ROUTE_MISSING",
        },
    )
    hashes["HISTORICAL_FCS_GAME_ACQUISITION_AND_RECONCILIATION_GATE.json"] = write_json(
        ART / "HISTORICAL_FCS_GAME_ACQUISITION_AND_RECONCILIATION_GATE.json",
        {
            "state": "BLOCKED",
            "fcs_v_fcs_acquired": False,
            "parent_identity": parent_identity,
        },
    )
    hashes["LOWER_DIVISION_STRENGTH_AND_CROSS_DIVISION_CALIBRATION_GATE.json"] = (
        write_json(
            ART / "LOWER_DIVISION_STRENGTH_AND_CROSS_DIVISION_CALIBRATION_GATE.json",
            {"state": "BLOCKED", "affected_forecasts_must_abstain": True},
        )
    )
    hashes["PIT_KERNEL_POPULATION_SCOPE_AND_SUBDIVISION_GATE.json"] = write_json(
        ART / "PIT_KERNEL_POPULATION_SCOPE_AND_SUBDIVISION_GATE.json",
        {
            "estimand": "FBS_ROUTE_OBSERVED_NOT_COMPLETE_EXPECTED_FBS_UNIVERSE",
            "expected_from_observed_cfbd_fbs_route": False,
            "state": "BLOCKED_EXPECTED_POPULATION",
            "parent_identity": parent_identity,
        },
    )
    hashes["FCS_AFFECTED_FORECAST_DEPRECATION_MAP.json"] = write_json(
        ART / "FCS_AFFECTED_FORECAST_DEPRECATION_MAP.json",
        {
            "successor_must_emit": [
                "ABSTAIN_HISTORICAL_COMPETITION_GRAPH_INCOMPLETE",
                "ABSTAIN_CROSS_SUBDIVISION_STRENGTH_NOT_ESTABLISHED",
            ],
            "fitted_forecasts_remain_immutable_predecessor": True,
        },
    )
    hashes["MISSOURI_STATE_RAW_TO_PRIOR_LINEAGE_TRACE.json"] = write_json(
        ART / "MISSOURI_STATE_RAW_TO_PRIOR_LINEAGE_TRACE.json",
        {
            "generator": "general_transition_program_logic",
            "focus_game_hardcode": False,
            "program_id": "MISSOURI_STATE",
            "admitted_prior_games": 52,
            "spine_edges_1963_2025": 66,
            "distinct_opponents": 32,
            "fcs_v_fcs": 0,
            "prior_supported": False,
            "omitted_fcs_schedule_coverage": "NOT_IN_FBS_FILTERED_ROUTE",
        },
    )

    catalog = canonical_catalog()
    xwalk = crosswalk()
    hashes["BAS_CANONICAL_DOMAIN_CATALOG.json"] = write_json(
        ART / "BAS_CANONICAL_DOMAIN_CATALOG.json", catalog
    )
    hashes["BAS_DOMAIN_CATALOG_CROSSWALK.json"] = write_json(
        ART / "BAS_DOMAIN_CATALOG_CROSSWALK.json", xwalk
    )
    hashes["BAS_DOMAIN_POPULATION_AND_GRAIN_CONTRACT.json"] = write_json(
        ART / "BAS_DOMAIN_POPULATION_AND_GRAIN_CONTRACT.json", grain_contract()
    )
    hashes["NATIONAL_DOMAIN_SOURCE_AND_RIGHTS_REGISTRY.json"] = write_json(
        ART / "NATIONAL_DOMAIN_SOURCE_AND_RIGHTS_REGISTRY.json",
        {"rights_reviewed": False, "contact_personal_data_not_retained": True},
    )
    hashes["NATIONAL_DOMAIN_RAW_PAYLOAD_INVENTORY.json"] = write_json(
        ART / "NATIONAL_DOMAIN_RAW_PAYLOAD_INVENTORY.json",
        {
            "forecast_rows_present": FORECAST_ROWS.is_file(),
            "people_registry_present": PEOPLE_CSV.is_file(),
            "missing_payloads_remain_blocked": True,
        },
    )
    domain_cells = [
        {
            "domain": row["canonical_domain_id"],
            "population": "national_historical",
            "disposition": "BLOCKED_INSUFFICIENT_EVIDENCE",
            "not_applicable": False,
        }
        for row in catalog["domains"]
        if row["kind"] == "DATA_DOMAIN"
    ]
    hashes["NATIONAL_DOMAIN_EXPECTED_OPPORTUNITY_CELLS.jsonl"] = write_jsonl(
        EXT / "NATIONAL_DOMAIN_EXPECTED_OPPORTUNITY_CELLS.jsonl", domain_cells
    )
    hashes["NATIONAL_DOMAIN_COVERAGE_CUBE.jsonl"] = write_jsonl(
        EXT / "NATIONAL_DOMAIN_COVERAGE_CUBE.jsonl",
        [{**cell, "numerator": 0, "denominator": 1} for cell in domain_cells],
    )
    hashes["NATIONAL_VERSUS_TAMU_COVERAGE_PARITY.json"] = write_json(
        ART / "NATIONAL_VERSUS_TAMU_COVERAGE_PARITY.json",
        {
            "grain": "program-season",
            "incompatible_collapse": False,
            "tamu_cannot_fill_national": True,
        },
    )
    hashes["NATIONAL_DOMAIN_PIT_AND_ADMISSION_GATE.json"] = write_json(
        ART / "NATIONAL_DOMAIN_PIT_AND_ADMISSION_GATE.json",
        {"state": "BLOCKED", "empty_empty_cannot_pass": True},
    )
    hashes["NATIONAL_DATA_GAP_AND_BACKFILL_LEDGER.jsonl"] = write_jsonl(
        EXT / "NATIONAL_DATA_GAP_AND_BACKFILL_LEDGER.jsonl",
        [
            {
                "gap": "independent_1963_2026_membership",
                "owner": "BAT-703",
                "finding": "C28-P0-11",
            },
            {
                "gap": "fcs_v_fcs_game_graph",
                "owner": "BAT-703",
                "finding": "C28-P0-12",
                "substantial_owner_if_split": "POST-TASK-NATIONAL-HISTORICAL-FCS-GAME-SPINE-AND-CROSS-SUBDIVISION-STRENGTH-001",
            },
        ],
    )
    hashes["NATIONAL_DATA_AFFECTED_MODEL_LINEAGE.json"] = write_json(
        ART / "NATIONAL_DATA_AFFECTED_MODEL_LINEAGE.json",
        {"fitted_forecasts": "UNTRUSTED_SHADOW", "abstain": True},
    )
    hashes["NATIONAL_DATA_COMPLETENESS_SUCCESSOR_GATE.json"] = write_json(
        ART / "NATIONAL_DATA_COMPLETENESS_SUCCESSOR_GATE.json",
        {"result": "BLOCKED_NOT_COMPLETE", "week1_is_not_national": True},
    )

    games, outcomes = fixture_kernel_games()
    compatibility_kernel = build_game_grain_kernel(
        games,
        outcomes,
        expected_population_complete=False,
        contemporaneous_fbs_authority=True,
        cross_subdivision=False,
    )
    reconstructed = reconstruct_game_features(games, outcomes)
    reconstruction = compare_producer_rows(compatibility_kernel["rows"], reconstructed)
    hashes["PIT_KERNEL_BOUNDED_COMPATIBILITY_FIXTURE.json"] = write_json(
        ART / "PIT_KERNEL_BOUNDED_COMPATIBILITY_FIXTURE.json",
        {
            "row_class": "BOUNDED_COMPATIBILITY_FIXTURE",
            "fixture_game_count": len(games),
            "reconstructed_fixture_rows": compatibility_kernel[
                "proven_pit_training_rows"
            ],
            "not_proven_pit_training_rows": True,
        },
    )
    production_kernel = {
        **compatibility_kernel,
        "proven_pit_training_rows": 0,
        "oriented_row_count": 0,
        "game_grain_count": 0,
        "rows": [],
        "oriented_rows": [],
        "blockers": list(compatibility_kernel["blockers"])
        + [
            {
                "canonical_game_id": None,
                "blocker": "NO_AUTHORITY_CLEAN_HISTORICAL_MEMBERSHIP_POPULATION",
            }
        ],
        "blocker_count": int(compatibility_kernel["blocker_count"]) + 1,
        "compatibility_fixture_row_count": compatibility_kernel[
            "proven_pit_training_rows"
        ],
    }
    hashes["PIT_KERNEL_ROWS.jsonl"] = write_jsonl(
        EXT / "PIT_KERNEL_ROWS.jsonl", production_kernel["rows"]
    )
    hashes["PIT_KERNEL_EXCLUSION_LEDGER.jsonl"] = write_jsonl(
        EXT / "PIT_KERNEL_EXCLUSION_LEDGER.jsonl", production_kernel["blockers"]
    )
    recon_pop = predecessor_reconciliation(
        pit_feature_eligible=89855,
        oriented_development=90198,
        active_proven=0,
        kernel_proven=int(production_kernel["proven_pit_training_rows"]),
    )
    hashes["PIT_PREDECESSOR_POPULATION_RECONCILIATION.json"] = write_json(
        ART / "PIT_PREDECESSOR_POPULATION_RECONCILIATION.json", recon_pop
    )
    hashes["PIT_KERNEL_DOMAIN_ADMISSION.json"] = write_json(
        ART / "PIT_KERNEL_DOMAIN_ADMISSION.json",
        {
            "admitted": production_kernel["admitted_domains"],
            "excluded": production_kernel["excluded_domains"],
        },
    )
    hashes["PIT_KERNEL_POPULATION_MANIFEST.json"] = write_json(
        ART / "PIT_KERNEL_POPULATION_MANIFEST.json",
        {
            "scope": production_kernel["scope"],
            "proven_pit_training_rows": production_kernel["proven_pit_training_rows"],
            "game_grain_count": production_kernel["game_grain_count"],
            "oriented_row_count": production_kernel["oriented_row_count"],
            "compatibility_fixture_row_count": production_kernel[
                "compatibility_fixture_row_count"
            ],
        },
    )
    hashes["PIT_KERNEL_TEMPORAL_PROOF.json"] = write_json(
        ART / "PIT_KERNEL_TEMPORAL_PROOF.json",
        {"aware_utc": True, "date_only_uses_bat666_bounds": True},
    )
    hashes["PIT_KERNEL_RAW_TO_ROW_TRACE_SAMPLE.json"] = write_json(
        ART / "PIT_KERNEL_RAW_TO_ROW_TRACE_SAMPLE.json",
        {
            "sample": [],
            "reason": "NO_AUTHORITY_CLEAN_HISTORICAL_MEMBERSHIP_POPULATION",
        },
    )
    hashes["PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json"] = write_json(
        ART / "PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json",
        {
            **reconstruction,
            "reference": "aggie_analytics.scientific_reference.cycle29.pit",
            "applies_to": "BOUNDED_COMPATIBILITY_FIXTURE",
            "production_proven_rows": 0,
        },
    )
    hashes["PIT_KERNEL_MODEL_BASELINE.json"] = write_json(
        ART / "PIT_KERNEL_MODEL_BASELINE.json",
        {"no_candidate_promotion": True, "no_aandm_conclusion": True},
    )
    hashes["PIT_MODEL_LINEAGE_AND_DEPRECATION_MAP.json"] = write_json(
        ART / "PIT_MODEL_LINEAGE_AND_DEPRECATION_MAP.json",
        {
            "cycle28_fitted": "UNTRUSTED_SHADOW",
            "kernel_does_not_recover_fitted_trust": True,
        },
    )
    usable_gate = kernel_trust_gate(
        proven_rows=int(production_kernel["proven_pit_training_rows"]),
        independently_reconstructed=True,
        kernel_gates_pass=False,
        unresolved_p0_affects_kernel=True,
    )
    hashes["PIT_KERNEL_TRUST_GATE.json"] = write_json(
        ART / "PIT_KERNEL_TRUST_GATE.json", usable_gate
    )

    claims = kernel_closure_claims()
    discovered = discover_authority_claims(ART, claims)
    inventory = inventory_claims(claims, discovered)
    hashes["CYCLE29_CLAIM_INVENTORY.json"] = write_json(
        ART / "CYCLE29_CLAIM_INVENTORY.json",
        {
            "claims": claims,
            "unmapped_count": inventory["unmapped_count"],
            "discovered_count": inventory["discovered_count"],
            "all_cycle_trust_recovered": False,
        },
    )
    hashes["CYCLE29_FINDING_SUCCESSOR_LEDGER.json"] = write_json(
        ART / "CYCLE29_FINDING_SUCCESSOR_LEDGER.json", successor_ledger()
    )
    hashes["CYCLE29_DEPENDENCY_SEPARATION.json"] = write_json(
        ART / "CYCLE29_DEPENDENCY_SEPARATION.json",
        static_import_graph(ROOT / "src"),
    )

    forecast_proof: dict[str, Any]
    if FORECAST_ROWS.is_file():
        forecast_proof = rehash_payload(FORECAST_ROWS, FORECAST_SHA, 455)
        sample = []
        with FORECAST_ROWS.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= 455:
                    break
                if line.strip():
                    sample.append(json.loads(line))
        forecast_proof["issued"] = prove_issued_before_cutoff(sample)
        forecast_proof["candidates"] = sorted(
            {row.get("candidate_id") for row in sample}
        )
    else:
        forecast_proof = {"result": "BLOCKED_PAYLOAD_UNAVAILABLE", "expected_rows": 455}
    hashes["CYCLE29_FORECAST_IMMUTABILITY.json"] = write_json(
        ART / "CYCLE29_FORECAST_IMMUTABILITY.json", forecast_proof
    )

    pos_contract = position_role_contract(ROLE_FAMILIES)
    hashes["POSITION_ROLE_OPPORTUNITY_CONTRACT.json"] = write_json(
        ART / "POSITION_ROLE_OPPORTUNITY_CONTRACT.json", pos_contract
    )
    week1_programs = list(week1["programs"])
    week1_matrix = hc_oc_dc_matrix(week1_programs, AS_OF)
    hashes["WEEK1_2026_HC_OC_DC_ROLE_MATRIX.jsonl"] = write_jsonl(
        EXT / "WEEK1_2026_HC_OC_DC_ROLE_MATRIX.jsonl", week1_matrix
    )
    hashes["CURRENT_2026_NATIONAL_HC_OC_DC_ROLE_MATRIX.jsonl"] = write_jsonl(
        EXT / "CURRENT_2026_NATIONAL_HC_OC_DC_ROLE_MATRIX.jsonl",
        [
            {
                "matrix_state": "BLOCKED_PARENT_POPULATION_UNENUMERATED",
                "required_formula": "3 * N",
                "N": None,
                "cell_count_is_not_a_denominator": True,
            }
        ],
    )
    current_lattice = [
        {
            "program_id": None,
            "role_family": role,
            "as_of_utc": AS_OF,
            "applicability": "APPLICABILITY_UNRESOLVED",
            "parent_blocked": True,
        }
        for role in ROLE_FAMILIES
    ]
    hashes["CURRENT_2026_NATIONAL_POSITION_ROLE_OPPORTUNITY_LATTICE.jsonl"] = (
        write_jsonl(
            EXT / "CURRENT_2026_NATIONAL_POSITION_ROLE_OPPORTUNITY_LATTICE.jsonl",
            current_lattice,
        )
    )
    hist_ps = [
        {"program_id": "BLOCKED_MEMBERSHIP", "season": year}
        for year in range(1963, 2027)
    ]
    hist_lattice = historical_lattice(hist_ps, ROLE_FAMILIES)
    hashes["HISTORICAL_NATIONAL_POSITION_ROLE_OPPORTUNITY_LATTICE.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_NATIONAL_POSITION_ROLE_OPPORTUNITY_LATTICE.jsonl",
        hist_lattice,
    )
    hashes["HISTORICAL_NATIONAL_PROGRAM_SEASON_ROLE_LATTICE.jsonl"] = write_jsonl(
        EXT / "HISTORICAL_NATIONAL_PROGRAM_SEASON_ROLE_LATTICE.jsonl",
        historical_lattice(
            hist_ps,
            PRIMARY := ("head_coach", "offensive_coordinator", "defensive_coordinator"),
        ),
    )
    del PRIMARY

    coaching_recon: dict[str, Any]
    if PEOPLE_CSV.is_file():
        extracted = extract_registry_identities(PEOPLE_CSV)
        coaching_recon = reconcile_predecessor_observations(
            extracted["accepted_ids"], extracted["provisional"]
        )
        write_jsonl(
            EXT / "PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.jsonl",
            coaching_recon["rows"],
        )
        coaching_recon = {k: v for k, v in coaching_recon.items() if k != "rows"} | {
            "accepted_count": len(extracted["accepted_ids"]),
            "provisional_count": len(extracted["provisional"]),
            "external_jsonl": "ops/cycle29_work/outputs/PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.jsonl",
        }
    else:
        coaching_recon = {"state": "BLOCKED_PAYLOAD_UNAVAILABLE"}
    hashes["PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.json"] = write_json(
        ART / "PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.json", coaching_recon
    )
    hashes["OFFICIAL_STAFF_SOURCE_REGISTRY.json"] = write_json(
        ART / "OFFICIAL_STAFF_SOURCE_REGISTRY.json",
        {"personal_contact_data_not_retained": True, "cfbd_scope": "head_coach_only"},
    )
    for name in (
        "COACH_IDENTITY_GRAPH.jsonl",
        "COACH_SOURCE_OBSERVATIONS.jsonl",
        "COACH_EMPLOYMENT_EPISODES.jsonl",
        "FORMAL_TITLE_EPISODES.jsonl",
        "RESPONSIBILITY_EPISODES.jsonl",
        "HISTORICAL_NATIONAL_COACH_BACKBONE.jsonl",
        "HISTORICAL_NATIONAL_COACHING_EPISODE_GRAPH.jsonl",
        "HISTORICAL_COACHING_BACKFILL_LEDGER.jsonl",
    ):
        hashes[name] = write_jsonl(
            EXT / name, [{"state": "QUEUED_OR_CANDIDATE", "model_admitted": False}]
        )
    hashes["POSITION_COACH_NATIONAL_ACQUISITION_TRANCHE.json"] = write_json(
        ART / "POSITION_COACH_NATIONAL_ACQUISITION_TRANCHE.json",
        {
            "attempted": True,
            "completeness_claimed": False,
            "discovered_titles_do_not_define_denominator": True,
        },
    )
    hashes["COACHING_CONFLICT_AND_ADJUDICATION_LEDGER.json"] = write_json(
        ART / "COACHING_CONFLICT_AND_ADJUDICATION_LEDGER.json",
        {"conflicts": [], "manual_queue": True},
    )
    hashes["COACHING_COVERAGE_AND_RIGHTS_GATE.json"] = write_json(
        ART / "COACHING_COVERAGE_AND_RIGHTS_GATE.json",
        {
            "CURRENT_NATIONAL_HC_OC_DC_COMPLETE": False,
            "NATIONAL_COACHING_PROGRAM_COMPLETE": False,
            "NATIONAL_ACQUISITION_ATTEMPTED_WITH_EXPLICIT_GAPS": True,
            "week1_cells": len(week1_matrix),
            "W": w,
        },
    )
    hashes["COACHING_MODEL_ADMISSION_GATE.json"] = write_json(
        ART / "COACHING_MODEL_ADMISSION_GATE.json", model_admission_gate()
    )

    hashes["CYCLE29_ALL22_SNAPSHOT.json"] = write_json(
        ART / "CYCLE29_ALL22_SNAPSHOT.json",
        {
            "c01_consumed": False,
            "c01_state": "BLOCKED_NO_IMMUTABLE_RELEASE_BOM",
            "synthetic_fixtures_bounded": True,
            "issued_at_utc": issued,
        },
    )
    hashes["GRIDIRON_COACHING_CONTRACT_VNEXT.json"] = write_json(
        ART / "GRIDIRON_COACHING_CONTRACT_VNEXT.json",
        {
            "contract_id": "GRIDIRON-COACHING-CONTRACT-VNEXT-CYCLE29",
            "role_level_unknowns_explicit": True,
        },
    )

    try:
        head = git("rev-parse", "HEAD")
        branch = git("branch", "--show-current")
    except subprocess.CalledProcessError:
        head = "UNKNOWN"
        branch = "UNKNOWN"
    hashes["CYCLE29_PREFLIGHT_AND_PRESERVATION.json"] = write_json(
        ART / "CYCLE29_PREFLIGHT_AND_PRESERVATION.json",
        {
            "artifact_type": "CYCLE29_PREFLIGHT_AND_PRESERVATION",
            "issued_at_utc": issued,
            "science_head": head,
            "science_branch": branch,
            "main_observed": "55e12a5aad3a7e843204fcba619c3cb3d3d6194d",
            "hold_active": True,
            "dependabot_654_untouched": True,
            "migration": "DEFERRED_BY_USER_NOT_COMPLETE",
            "public_repo_canonical": True,
        },
    )
    hashes["CYCLE29_MATERIALIZATION_MANIFEST.json"] = write_json(
        ART / "CYCLE29_MATERIALIZATION_MANIFEST.json",
        {"issued_at_utc": issued, "file_hashes": hashes, "operator_hold": "ACTIVE"},
    )
    print(
        json.dumps(
            {
                "ok": True,
                "files": len(hashes),
                "W": w,
                "proven": production_kernel["proven_pit_training_rows"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
