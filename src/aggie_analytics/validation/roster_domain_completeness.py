from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.validation.protected_split_authority import sha256_file

SCHEMA_VERSION = "aggie.validation.roster_domain_completeness.v2"
CONTRACT_RELATIVE = "configs/roster_domain_completeness_contract.json"
GATE_RELATIVE = "artifacts/pit/roster_domain_completeness_gate.json"
CONTRACT_ID = "BAT-567-ROSTER-DOMAIN-COMPLETENESS-V2"
PASS_RESULT = "PASS_ROSTER_DOMAIN_COMPLETENESS_AVAILABILITY_BLOCKED"
PASS_CLASSIFICATION = "ROSTER_DOMAIN_COMPLETENESS_AVAILABILITY_BLOCKED"
SUPERSEDED_GATE_IDENTITY = "15f68c244da9697ca70c128eed24e6498302bebff9a085220fcb488e041d413c"
PROTECTED_SEASONS = frozenset({2024, 2025})
NON_AUTHORITATIVE_METADATA = ("issued_at_utc",)
RECONSTRUCTED_COUNT_INTERPRETATION = (
    "reconstructed exact-membership rows matching the existing BAT-546 admission"
)
EXACT_MEMBERSHIP_FILTER_SPEC = {
    "reconciliation_disposition": (
        "CANDIDATE_CROSS_ROUTE_IDENTITY_EXACT_ROSTER_CANONICAL_PLAYER_MEMBERSHIP"
    ),
    "canonical_player_id_not_null": True,
    "canonical_team_id_not_null": True,
    "canonical_player_id_equals_canonical_membership_player_id": True,
    "canonical_membership_resolution_state": "AUTO_ACCEPTED_VERIFIED",
    "team_label_exact_match": True,
    "canonical_membership_exact_team_option_count": 1,
    "canonical_membership_ambiguous": False,
    "athlete_id_occurrence": 0,
}
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "input_identities",
    "parent_identities",
    "payload_probe",
    "reconstructed",
    "admissions",
    "missing_availability_evidence",
    "remaining_blockers",
    "exact_membership_filter_identity",
    "authority",
    "scientific_nonclaims",
    "issue_completion",
    "supersession",
)


class AvailabilityAdmissionDenied(RuntimeError):
    """Raised when availability is inferred from membership or postgame participation."""


class PayloadMountRequired(RuntimeError):
    """Raised when a new membership layer is requested without mounted source payloads."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = repo_root / CONTRACT_RELATIVE
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("roster completeness contract identity drift")
    if contract.get("authority", {}).get("availability_admission") is not False:
        raise AvailabilityAdmissionDenied("contract must fail-close availability admission")
    if contract.get("authority", {}).get("protected_evaluation_admission") is not False:
        raise AvailabilityAdmissionDenied("contract must fail-close protected evaluation admission")
    if contract.get("authority", {}).get("champion_or_production_promotion") is not False:
        raise AvailabilityAdmissionDenied("contract must fail-close champion or production promotion")
    if contract.get("authority", {}).get("new_membership_layer_materialization") is not False:
        raise PayloadMountRequired("contract must not authorize a new membership layer")
    if contract.get("exact_membership_filter_spec") != EXACT_MEMBERSHIP_FILTER_SPEC:
        raise ValueError("exact-membership filter spec drifted from the bound implementation")
    return contract


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_file(path: Path, expected_sha256: str, context: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{context} is missing: {path}")
    digest = sha256_file(path)
    if digest != expected_sha256:
        raise ValueError(f"{context} hash drift: {digest}")
    return {"path": str(path), "sha256": digest, "bytes": path.stat().st_size}


def probe_payloads(data_root: Path, relative_paths: list[str]) -> dict[str, Any]:
    probes: list[dict[str, Any]] = []
    present = 0
    for relative in relative_paths:
        path = data_root / Path(relative)
        exists = path.exists()
        present += int(exists)
        probes.append(
            {
                "relative_path": relative,
                "exists": exists,
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
            }
        )
    return {
        "probed": len(probes),
        "present": present,
        "absent": len(probes) - present,
        "mount_state": "PRESENT" if present == len(probes) else ("PARTIAL" if present else "ABSENT"),
        "probes": probes,
    }


def _season_disposition_total(summaries: list[Mapping[str, Any]], disposition: str) -> int:
    total = 0
    for row in summaries:
        for item in row.get("disposition_counts", []):
            if item.get("disposition") == disposition:
                total += int(item["rows"])
    return total


def inspect_roster_history(data_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    identities = contract["identities"]
    acceptance = contract["acceptance"]
    path = data_root / identities["roster_history_manifest_relative_path"]
    verify_file(path, identities["roster_history_manifest_sha256"], "roster history manifest")
    manifest = load_json(path)
    if manifest.get("dataset_identity") != identities["roster_history_dataset_identity"]:
        raise ValueError("roster history dataset identity drift")
    summaries = manifest["population"]["season_summaries"]
    seasons = [int(row["season"]) for row in summaries]
    exact = _season_disposition_total(
        summaries, "CANDIDATE_CROSS_ROUTE_IDENTITY_EXACT_ROSTER_CANONICAL_PLAYER_MEMBERSHIP"
    )
    source_only = _season_disposition_total(
        summaries, "CANDIDATE_VERSIONED_REPOSITORY_ROSTER_SOURCE_LEVEL_ONLY"
    )
    ambiguous = _season_disposition_total(summaries, "QUARANTINE_CANONICAL_ROSTER_MEMBERSHIP_AMBIGUOUS")
    name_conflicts = _season_disposition_total(
        summaries, "QUARANTINE_CURRENT_ROSTER_ATHLETE_NAME_CONFLICT"
    )
    match_ambiguity = _season_disposition_total(
        summaries, "QUARANTINE_CURRENT_ROSTER_MATCH_AMBIGUOUS"
    )
    invalid_core = _season_disposition_total(summaries, "QUARANTINE_INVALID_VERSIONED_ROSTER_CORE")
    reconstructed = {
        "source_rows": int(manifest["population"]["repository_rows"]),
        "seasons": seasons,
        "exact_membership_candidates": exact,
        "source_level_only": source_only,
        "ambiguous_membership": ambiguous,
        "name_conflicts": name_conflicts,
        "match_ambiguity": match_ambiguity,
        "invalid_core": invalid_core,
        "count_source": "PINNED_MANIFEST_SEASON_SUMMARIES",
    }
    expected = {
        "source_rows": acceptance["roster_history_source_rows"],
        "seasons": acceptance["roster_history_seasons"],
        "exact_membership_candidates": acceptance["roster_history_exact_membership_candidates"],
        "source_level_only": acceptance["roster_history_source_level_only"],
        "ambiguous_membership": acceptance["roster_history_ambiguous_membership"],
        "name_conflicts": acceptance["roster_history_name_conflicts"],
        "match_ambiguity": acceptance["roster_history_match_ambiguity"],
        "invalid_core": acceptance["roster_history_invalid_core"],
    }
    if {k: reconstructed[k] for k in expected} != expected:
        raise ValueError("roster history reconstructed counts drifted from the pinned contract")
    return reconstructed


def inspect_post2022(data_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    identities = contract["identities"]
    acceptance = contract["acceptance"]
    path = data_root / identities["post2022_manifest_relative_path"]
    verify_file(path, identities["post2022_manifest_sha256"], "post-2022 roster manifest")
    manifest = load_json(path)
    if manifest.get("dataset_identity") != identities["post2022_dataset_identity"]:
        raise ValueError("post-2022 dataset identity drift")
    if set(int(season) for season in manifest.get("seasons", [])) & PROTECTED_SEASONS != {2024, 2025}:
        raise ValueError("post-2022 population lost protected seasons or silently dropped them")
    if manifest.get("authority", {}).get("asset_updated_at_is_historical_game_known_at") is not False:
        raise ValueError("post-2022 timestamps must not be treated as historical known-at")
    if manifest.get("authority", {}).get("roster_membership_implies_availability") is not False:
        raise AvailabilityAdmissionDenied("post-2022 contract inferred availability from membership")
    reconstructed = {
        "source_rows": int(manifest["total_rows"]),
        "seasons": [int(season) for season in manifest["seasons"]],
        "exact_membership_candidates": int(
            manifest["disposition_counts"]["CANDIDATE_EXACT_SOURCE_ID_NAME_AND_CANONICAL_MEMBERSHIP"]
        ),
        "person_pending": int(manifest["disposition_counts"]["CANDIDATE_CANONICAL_PERSON_MEMBERSHIP_PENDING"]),
        "source_level_only": int(manifest["disposition_counts"]["CANDIDATE_SOURCE_LEVEL_ONLY"]),
        "quarantine_conflicts": int(manifest["disposition_counts"]["QUARANTINE_SOURCE_ID_NAME_CONFLICT"]),
        "historical_known_at_eligible": False,
        "count_source": "PINNED_MANIFEST_DISPOSITION_COUNTS",
    }
    expected = {
        "source_rows": acceptance["post2022_source_rows"],
        "seasons": acceptance["post2022_seasons"],
        "exact_membership_candidates": acceptance["post2022_exact_membership_candidates"],
        "person_pending": acceptance["post2022_person_pending"],
        "source_level_only": acceptance["post2022_source_level_only"],
        "quarantine_conflicts": acceptance["post2022_quarantine_conflicts"],
    }
    if {k: reconstructed[k] for k in expected} != expected:
        raise ValueError("post-2022 reconstructed counts drifted from the pinned contract")
    return reconstructed


def inspect_team_membership(data_root: Path, repo_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    identities = contract["identities"]
    acceptance = contract["acceptance"]
    path = data_root / identities["team_membership_manifest_relative_path"]
    verify_file(path, identities["team_membership_manifest_sha256"], "team-membership manifest")
    manifest = load_json(path)
    if manifest.get("dataset_identity") != identities["team_membership_dataset_identity"]:
        raise ValueError("team-membership dataset identity drift")
    gate = load_json(repo_root / identities["bat547_gate_relative_path"])
    if gate.get("output_identities", {}).get("dataset") != identities["bat547_admitted_dataset_identity"]:
        raise ValueError("BAT-547 admitted identity drift")
    reconstructed = {
        "source_rows": int(manifest["population"]["repository_rows"]),
        "admitted_rows": int(gate["population"]["admitted_rows"]),
        "seasons": [int(row["season"]) for row in manifest["population"]["season_summaries"]],
        "duplicate_natural_keys": int(gate["population"]["duplicate_natural_keys"]),
        "count_source": "PINNED_MANIFEST_AND_BAT547_GATE",
    }
    if (
        reconstructed["source_rows"] != acceptance["team_membership_source_rows"]
        or reconstructed["admitted_rows"] != acceptance["team_membership_admitted_rows"]
        or reconstructed["seasons"] != acceptance["team_membership_seasons"]
    ):
        raise ValueError("team-membership reconstructed counts drifted from the pinned contract")
    return reconstructed


def inspect_tamu_gamebook(data_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    identities = contract["identities"]
    acceptance = contract["acceptance"]
    path = data_root / identities["tamu_gamebook_manifest_relative_path"]
    verify_file(path, identities["tamu_gamebook_manifest_sha256"], "TAMU gamebook manifest")
    manifest = load_json(path)
    if manifest.get("dataset_identity") != identities["tamu_gamebook_dataset_identity"]:
        raise ValueError("TAMU gamebook dataset identity drift")
    domains = {row["domain"]: row for row in manifest["domain_summaries"]}
    if "availability" in domains:
        raise AvailabilityAdmissionDenied("gamebook availability domain appeared without a pregame contract")
    eligibility = manifest["eligibility_contract"]
    if "NOT_PROVIDED" not in str(eligibility.get("availability", "")):
        raise AvailabilityAdmissionDenied("gamebook eligibility lost the availability NOT_PROVIDED bound")
    reconstructed = {
        "games": int(manifest["population"]["source_games"]),
        "player_rows": int(domains["players"]["rows"]),
        "availability_rows": 0,
        "availability_domain_present": False,
        "gap_seasons": [2010, 2011],
        "historical_known_at_state": "UNKNOWN_EXACT_PUBLICATION_TIME_CAPTURE_TIME_ONLY",
        "count_source": "PINNED_MANIFEST_DOMAIN_SUMMARIES",
        "national_coverage": False,
        "tamu_only": True,
    }
    if (
        reconstructed["games"] != acceptance["tamu_gamebook_games"]
        or reconstructed["player_rows"] != acceptance["tamu_gamebook_player_rows"]
        or reconstructed["availability_rows"] != acceptance["tamu_gamebook_availability_rows"]
        or reconstructed["gap_seasons"] != acceptance["tamu_gamebook_gap_seasons"]
    ):
        raise ValueError("TAMU gamebook reconstructed counts drifted from the pinned contract")
    return reconstructed


def inspect_existing_membership_admission(repo_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    identities = contract["identities"]
    acceptance = contract["acceptance"]
    gate = load_json(repo_root / identities["bat546_gate_relative_path"])
    if gate.get("output_identities", {}).get("dataset") != identities["bat546_admitted_dataset_identity"]:
        raise ValueError("BAT-546 admitted identity drift")
    if gate.get("authority", {}).get("game_time_availability_authority") is not False:
        raise AvailabilityAdmissionDenied("BAT-546 gate granted availability authority")
    if gate.get("authority", {}).get("season_membership_only") is not True:
        raise ValueError("BAT-546 gate lost season-membership-only authority")
    reconstructed = {
        "admitted_rows": int(gate["population"]["admitted_rows"]),
        "nonadmitted_rows": int(gate["population"]["nonadmitted_rows"]),
        "distinct_players": int(gate["population"]["distinct_players"]),
        "distinct_teams": int(gate["population"]["distinct_teams"]),
        "multi_team_player_seasons": int(gate["population"]["multi_team_player_seasons"]),
        "duplicate_natural_keys": int(gate["population"]["duplicate_natural_keys"]),
        "count_source": "PINNED_BAT546_GATE",
    }
    expected = {
        "admitted_rows": acceptance["bat546_admitted_rows"],
        "nonadmitted_rows": acceptance["bat546_nonadmitted_rows"],
        "distinct_players": acceptance["bat546_distinct_players"],
        "distinct_teams": acceptance["bat546_distinct_teams"],
        "multi_team_player_seasons": acceptance["bat546_multi_team_player_seasons"],
        "duplicate_natural_keys": acceptance["bat546_duplicate_natural_keys"],
    }
    if reconstructed != {**expected, "count_source": "PINNED_BAT546_GATE"}:
        raise ValueError("BAT-546 reconstructed counts drifted from the pinned contract")
    return reconstructed


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("roster-domain completeness requires the optional data-engineering environment") from exc
    return polars


def _exact_membership_filter(pl: Any) -> Any:
    return (
        (pl.col("reconciliation_disposition") == "CANDIDATE_CROSS_ROUTE_IDENTITY_EXACT_ROSTER_CANONICAL_PLAYER_MEMBERSHIP")
        & pl.col("canonical_player_id").is_not_null()
        & pl.col("canonical_team_id").is_not_null()
        & (pl.col("canonical_player_id") == pl.col("canonical_membership_player_id"))
        & (pl.col("canonical_membership_resolution_state") == "AUTO_ACCEPTED_VERIFIED")
        & (pl.col("team_label_exact_match") == True)  # noqa: E712
        & (pl.col("canonical_membership_exact_team_option_count") == 1)
        & (pl.col("canonical_membership_ambiguous") == False)  # noqa: E712
        & (pl.col("athlete_id_occurrence") == 0)
    )


def inspect_tamu_versus_national(data_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    pl = _polars()
    history_root = data_root / contract["expected_payload_probes"][0]
    frames = [
        pl.read_parquet(path)
        for path in sorted(history_root.glob("season=*/candidate_roster_rows.parquet"))
    ]
    if not frames:
        raise FileNotFoundError("2004-2022 candidate roster payloads are not mounted")
    admitted = pl.concat(frames, how="diagonal_relaxed").filter(_exact_membership_filter(pl))
    tamu = admitted.filter(pl.col("canonical_team_label") == "Texas A&M")
    post_root = data_root / contract["expected_payload_probes"][2]
    post_frames = [
        pl.read_parquet(path)
        for path in sorted(post_root.glob("season=*/candidate_roster_rows.parquet"))
    ]
    if not post_frames:
        raise FileNotFoundError("post-2022 candidate roster payloads are not mounted")
    post = pl.concat(post_frames, how="diagonal_relaxed")
    post_tamu_exact = post.filter(
        (pl.col("team_label") == "Texas A&M")
        & (pl.col("reconciliation_disposition") == "CANDIDATE_EXACT_SOURCE_ID_NAME_AND_CANONICAL_MEMBERSHIP")
    )
    reconstructed = {
        "national_admitted_membership_rows": admitted.height,
        "national_admitted_players": admitted["canonical_player_id"].n_unique(),
        "national_admitted_teams": admitted["canonical_team_id"].n_unique(),
        "tamu_admitted_membership_rows_2004_2022": tamu.height,
        "tamu_admitted_membership_players_2004_2022": tamu["canonical_player_id"].n_unique(),
        "tamu_admitted_membership_seasons": sorted(tamu["season"].unique().to_list()),
        "tamu_post2022_exact_membership_candidates": post_tamu_exact.height,
        "tamu_membership_rows_independently_reconstructed": True,
        "count_source": "RECONSTRUCTED_EXACT_MEMBERSHIP_ROWS_MATCHING_EXISTING_BAT546_ADMISSION",
        "count_interpretation": RECONSTRUCTED_COUNT_INTERPRETATION,
        "new_membership_layer_created": False,
        "tamu_gamebook_player_rows": contract["acceptance"]["tamu_gamebook_player_rows"],
        "tamu_gamebook_availability_rows": 0,
    }
    acceptance = contract["acceptance"]
    if (
        reconstructed["tamu_admitted_membership_rows_2004_2022"]
        != acceptance["tamu_admitted_membership_rows_2004_2022"]
        or reconstructed["tamu_admitted_membership_players_2004_2022"]
        != acceptance["tamu_admitted_membership_players_2004_2022"]
        or reconstructed["tamu_post2022_exact_membership_candidates"]
        != acceptance["tamu_post2022_exact_membership_candidates"]
        or reconstructed["national_admitted_membership_rows"] != acceptance["bat546_admitted_rows"]
    ):
        raise ValueError("A&M versus national reconstructed counts drifted from the pinned contract")
    return reconstructed


def decide_admissions(payload_probe: Mapping[str, Any]) -> dict[str, Any]:
    if payload_probe["mount_state"] == "PRESENT":
        raise PayloadMountRequired("payloads are mounted; rematerialization must be an explicit later unit")
    return {
        "season_membership_2004_2022": "PRESERVE_EXISTING_BAT546_DEVELOPMENT_ONLY_ADMISSION",
        "team_membership_2001_2020": "PRESERVE_EXISTING_BAT547_DEVELOPMENT_ONLY_ADMISSION",
        "post2022_membership": "RETAIN_CANDIDATE_ONLY",
        "tamu_official_gamebook": "RETAIN_CANDIDATE_ONLY",
        "new_development_membership_layer": "NOT_MATERIALIZED_EXISTING_BAT546_ADMISSION_PRESERVED",
        "pregame_availability": "BLOCKED",
        "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
    }


def missing_availability_evidence() -> list[dict[str, str]]:
    return [
        {
            "code": "NO_PREGAME_PUBLICATION_OR_KNOWN_AT_FOR_AVAILABILITY",
            "detail": "No roster or gamebook source proves first-public pregame availability time.",
        },
        {
            "code": "MEMBERSHIP_IS_NOT_AVAILABILITY",
            "detail": "Season membership cannot be promoted to starter, injury, depth, practice, or availability.",
        },
        {
            "code": "POSTGAME_PARTICIPATION_IS_NOT_PREGAME_AVAILABILITY",
            "detail": "TAMU gamebook player rows are postgame participation candidates, not pregame availability.",
        },
        {
            "code": "POST2022_RELEASE_TIMESTAMPS_ARE_2026",
            "detail": "Post-2022 roster assets are not historical known-at evidence for 2023-2025 games.",
        },
        {
            "code": "GAMEBOOK_AVAILABILITY_ROWS_ZERO_AND_DOMAIN_ABSENT",
            "detail": "The official A&M gamebook capture has no availability domain and zero availability rows.",
        },
        {
            "code": "ADMITTED_MEMBERSHIP_PAYLOAD_NOT_MOUNTED",
            "detail": "The BAT-546 admitted membership parquet is absent. Candidate payloads remain and are used only for completeness counts.",
        },
    ]


def exact_membership_filter_identity() -> str:
    return stable_hash(EXACT_MEMBERSHIP_FILTER_SPEC)


def expected_parent_identities(contract: Mapping[str, Any]) -> dict[str, str]:
    identities = contract["identities"]
    return {
        "BAT-546_admitted_dataset": identities["bat546_admitted_dataset_identity"],
        "BAT-547_admitted_dataset": identities["bat547_admitted_dataset_identity"],
        "roster_history_dataset": identities["roster_history_dataset_identity"],
        "post2022_dataset": identities["post2022_dataset_identity"],
        "team_membership_dataset": identities["team_membership_dataset_identity"],
        "tamu_gamebook_dataset": identities["tamu_gamebook_dataset_identity"],
        "protected_split_registry": identities["protected_split_registry_sha256"],
    }


def expected_input_identities(contract: Mapping[str, Any]) -> dict[str, str]:
    identities = contract["identities"]
    return {
        key: identities[key]
        for key in (
            "roster_history_dataset_identity",
            "roster_history_manifest_sha256",
            "post2022_dataset_identity",
            "post2022_manifest_sha256",
            "team_membership_dataset_identity",
            "team_membership_manifest_sha256",
            "tamu_gamebook_dataset_identity",
            "tamu_gamebook_manifest_sha256",
            "bat546_admitted_dataset_identity",
            "bat547_admitted_dataset_identity",
            "protected_split_registry_sha256",
        )
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "historical_population_ready": False,
        "gap_002_resolved": False,
        "availability_admitted": False,
        "pregame_availability_admitted": False,
        "new_membership_layer_materialized": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_performance_claimed": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
    }


def expected_issue_completion(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "jira_key": contract["jira_key"],
        "workflow_state": "DONE",
        "logical_state": "DONE",
        "maturity": "IMPLEMENTED",
        "evidence_state": "VERIFIED",
        "issue_complete": True,
        "pregame_availability_still_blocked": True,
    }


def expected_supersession() -> dict[str, Any]:
    return {
        "supersedes_gate_identity": SUPERSEDED_GATE_IDENTITY,
        "superseded_reason": "V1_GATE_IDENTITY_DID_NOT_BIND_ALL_AUTHORITY_BEARING_SEMANTICS",
        "active": True,
    }


def expected_remaining_blockers() -> list[str]:
    return [row["code"] for row in missing_availability_evidence()]


def derive_authority_from_evidence(
    contract: Mapping[str, Any],
    reconstructed: Mapping[str, Any],
    payload_probe: Mapping[str, Any],
) -> dict[str, bool]:
    authority = dict(contract["authority"])
    gamebook = reconstructed.get("tamu_gamebook", {})
    versus = reconstructed.get("a_and_m_versus_national", {})
    if gamebook.get("availability_rows", 0) != 0 or gamebook.get("availability_domain_present"):
        raise AvailabilityAdmissionDenied("availability evidence appeared without a pregame contract")
    if versus.get("new_membership_layer_created") is True:
        raise PayloadMountRequired("reconstructed counts must not create a new membership layer")
    if payload_probe.get("mount_state") == "PRESENT":
        raise PayloadMountRequired("payloads are mounted; rematerialization must be an explicit later unit")
    for key in (
        "availability_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "protected_training_admission",
        "new_membership_layer_materialization",
    ):
        if authority.get(key) is not False:
            raise AvailabilityAdmissionDenied(f"contract authority {key} is not fail-closed")
    return authority


def derive_admissions_from_evidence(
    payload_probe: Mapping[str, Any],
    reconstructed: Mapping[str, Any],
) -> dict[str, str]:
    admissions = decide_admissions(payload_probe)
    gamebook = reconstructed.get("tamu_gamebook", {})
    if gamebook.get("availability_rows", 0) != 0:
        raise AvailabilityAdmissionDenied("gamebook availability rows cannot admit pregame availability")
    if admissions["pregame_availability"] != "BLOCKED":
        raise AvailabilityAdmissionDenied("pregame availability must remain blocked")
    if admissions["protected_lane"] != "RETAIN_PROTECTED_LANE_BLOCKED":
        raise AvailabilityAdmissionDenied("protected lane must remain blocked")
    return admissions


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate})


def identity_core(
    *,
    contract_sha256: str,
    input_identities: Mapping[str, str],
    payload_mount_state: str,
    reconstructed_counts: Mapping[str, Any],
    admissions: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "classification": PASS_CLASSIFICATION,
        "contract_sha256": contract_sha256,
        "input_identities": dict(input_identities),
        "payload_mount_state": payload_mount_state,
        "reconstructed_counts": reconstructed_counts,
        "admissions": dict(admissions),
        "availability_admission": False,
        "protected_evaluation_admission": False,
        "champion_or_production_promotion": False,
    }


def expected_gate_document(expected: Mapping[str, Any]) -> dict[str, Any]:
    contract = expected["contract"]
    reconstructed = expected["reconstructed"]
    payload_probe = expected["payload_probe"]
    admissions = derive_admissions_from_evidence(payload_probe, reconstructed)
    authority = derive_authority_from_evidence(contract, reconstructed, payload_probe)
    blockers = missing_availability_evidence()
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "ROSTER_DOMAIN_COMPLETENESS_AND_ADMISSION_GATE",
        "classification": PASS_CLASSIFICATION,
        "contract_id": contract["contract_id"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "result": PASS_RESULT,
        "input_identities": expected_input_identities(contract),
        "parent_identities": expected_parent_identities(contract),
        "payload_probe": payload_probe,
        "reconstructed": reconstructed,
        "admissions": admissions,
        "missing_availability_evidence": blockers,
        "remaining_blockers": [row["code"] for row in blockers],
        "exact_membership_filter_identity": exact_membership_filter_identity(),
        "authority": authority,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "issue_completion": expected_issue_completion(contract),
        "supersession": expected_supersession(),
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    registry = verify_file(
        repo_root / contract["identities"]["protected_split_registry_relative_path"],
        contract["identities"]["protected_split_registry_sha256"],
        "protected split registry",
    )
    payload_probe = probe_payloads(data_root, list(contract["expected_payload_probes"]))
    roster_history = inspect_roster_history(data_root, contract)
    post2022 = inspect_post2022(data_root, contract)
    team_membership = inspect_team_membership(data_root, repo_root, contract)
    tamu_gamebook = inspect_tamu_gamebook(data_root, contract)
    existing_membership = inspect_existing_membership_admission(repo_root, contract)
    tamu_versus_national = inspect_tamu_versus_national(data_root, contract)
    reconstructed = {
        "roster_history": roster_history,
        "existing_membership_admission": existing_membership,
        "post2022": post2022,
        "team_membership": team_membership,
        "tamu_gamebook": tamu_gamebook,
        "a_and_m_versus_national": tamu_versus_national,
    }
    admissions = derive_admissions_from_evidence(payload_probe, reconstructed)
    authority = derive_authority_from_evidence(contract, reconstructed, payload_probe)
    contract_sha256 = sha256_file(repo_root / CONTRACT_RELATIVE)
    expected = {
        "contract": contract,
        "contract_sha256": contract_sha256,
        "registry": registry,
        "payload_probe": payload_probe,
        "reconstructed": reconstructed,
        "admissions": admissions,
        "authority": authority,
        "missing_availability_evidence": missing_availability_evidence(),
        "remaining_blockers": expected_remaining_blockers(),
        "input_identities": expected_input_identities(contract),
        "parent_identities": expected_parent_identities(contract),
        "exact_membership_filter_identity": exact_membership_filter_identity(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "issue_completion": expected_issue_completion(contract),
        "supersession": expected_supersession(),
        "code_identity": sha256_file(Path(__file__).resolve()),
    }
    expected["gate_identity"] = expected_gate_document(expected)["gate_identity"]
    return expected


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    gate = expected_gate_document(expected)
    gate["issued_at_utc"] = issued_at_utc
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(gate) + b"\n")
    return {
        "gate_identity": gate["gate_identity"],
        "gate_path": str(path),
        "payload_mount_state": expected["payload_probe"]["mount_state"],
        "admissions": expected["admissions"],
        "supersedes": SUPERSEDED_GATE_IDENTITY,
    }


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate_path = repo_root / GATE_RELATIVE
    loaded_gate = dict(gate) if gate is not None else load_json(gate_path)
    if not require_rebuild:
        if loaded_gate.get("result") != PASS_RESULT:
            raise ValueError("gate result is not a roster-completeness pass with availability blocked")
        return {"result": "PASS", "mode": "gate_schema_only", "gate_identity": loaded_gate.get("gate_identity")}
    rebuilt = expected or rebuild_expected(data_root=data_root, repo_root=repo_root)
    expected_gate = expected_gate_document(rebuilt)
    errors: list[str] = []
    derived_parents = expected_parent_identities(rebuilt["contract"])
    if loaded_gate.get("parent_identities") != derived_parents:
        errors.append("parent identities were not derived from the authoritative contract")
    if loaded_gate.get("input_identities") != expected_input_identities(rebuilt["contract"]):
        errors.append("input identities were not derived from the authoritative contract")
    if loaded_gate.get("exact_membership_filter_identity") != exact_membership_filter_identity():
        errors.append("exact-membership filter identity drifted")
    derived_admissions = derive_admissions_from_evidence(rebuilt["payload_probe"], rebuilt["reconstructed"])
    derived_authority = derive_authority_from_evidence(
        rebuilt["contract"], rebuilt["reconstructed"], rebuilt["payload_probe"]
    )
    if loaded_gate.get("admissions") != derived_admissions:
        errors.append("admission decisions were accepted from the gate instead of derived from evidence")
    if loaded_gate.get("authority") != derived_authority:
        errors.append("authority fields were accepted from the gate instead of derived from evidence")
    if loaded_gate.get("payload_probe") != rebuilt["payload_probe"]:
        errors.append("payload-probe state drifted")
    if loaded_gate.get("reconstructed") != rebuilt["reconstructed"]:
        errors.append("reconstructed counts drifted")
    if loaded_gate.get("missing_availability_evidence") != missing_availability_evidence():
        errors.append("missing availability evidence drifted")
    if loaded_gate.get("remaining_blockers") != expected_remaining_blockers():
        errors.append("remaining blockers drifted")
    if loaded_gate.get("scientific_nonclaims") != expected_scientific_nonclaims():
        errors.append("scientific nonclaims drifted")
    if loaded_gate.get("issue_completion") != expected_issue_completion(rebuilt["contract"]):
        errors.append("issue completion state drifted")
    if loaded_gate.get("supersession") != expected_supersession():
        errors.append("supersession metadata drifted")
    if loaded_gate.get("result") != PASS_RESULT:
        errors.append("altered result/classification")
    if loaded_gate.get("classification") != PASS_CLASSIFICATION:
        errors.append("altered result/classification")
    if loaded_gate.get("admissions", {}).get("pregame_availability") != "BLOCKED":
        errors.append("pregame availability admitted")
    if loaded_gate.get("authority", {}).get("availability_admission") is not False:
        errors.append("pregame availability admitted")
    if loaded_gate.get("authority", {}).get("protected_evaluation_admission") is not False:
        errors.append("protected evaluation admission forged")
    if loaded_gate.get("authority", {}).get("champion_or_production_promotion") is not False:
        errors.append("champion or production promotion forged")
    if loaded_gate.get("scientific_nonclaims", {}).get("protected_performance_claimed") is not False:
        errors.append("protected-performance claim forged")
    if "MEMBERSHIP_IS_NOT_AVAILABILITY" not in loaded_gate.get("remaining_blockers", []):
        errors.append("missing availability blocker removed")
    if loaded_gate.get("gate_identity") == SUPERSEDED_GATE_IDENTITY:
        errors.append("superseded V1 gate identity is still active")
    for key in GATE_IDENTITY_FIELDS:
        if loaded_gate.get(key) != expected_gate.get(key):
            errors.append(f"gate.{key} is not independently reconstructed")
    independently_recomputed = compute_gate_identity(
        {key: loaded_gate[key] for key in GATE_IDENTITY_FIELDS if key in loaded_gate}
    )
    if loaded_gate.get("gate_identity") != expected_gate["gate_identity"]:
        errors.append("gate identity does not match independently reconstructed authority")
    if independently_recomputed == expected_gate["gate_identity"] and loaded_gate.get("result") != PASS_RESULT:
        errors.append("forged terminal state survived outer identity recomputation")
    if loaded_gate.get("gate_identity") != independently_recomputed:
        errors.append("claimed gate identity does not match recomputed outer identity")
    extra_authoritative = set(loaded_gate) - set(GATE_IDENTITY_FIELDS) - {"gate_identity"} - set(
        NON_AUTHORITATIVE_METADATA
    )
    if extra_authoritative:
        errors.append(f"undeclared authoritative keys {sorted(extra_authoritative)}")
    if errors:
        raise ValueError("independent roster-completeness validation failed: " + "; ".join(errors[:16]))
    return {
        "result": "PASS",
        "mode": "independent_rebuild",
        "gate_identity": expected_gate["gate_identity"],
        "payload_mount_state": rebuilt["payload_probe"]["mount_state"],
        "admissions": derived_admissions,
        "supersedes": SUPERSEDED_GATE_IDENTITY,
    }
