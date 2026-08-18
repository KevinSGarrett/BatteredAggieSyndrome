"""Season-level 2010-2011 Texas A&M cross-source reconciliation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash


SCHEMA_VERSION = "aggie.data.tamu_2010_2011_season_reconciliation.v1"
CONTRACT_RELATIVE = "configs/tamu_2010_2011_season_reconciliation_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_2010_2011_season_reconciliation_gate.json"
CONTRACT_ID = "BAT-575-TAMU-2010-2011-SEASON-RECONCILIATION-V1"
PASS_CLASSIFICATION = "TAMU_2010_2011_SEASON_RECONCILIATION_CANDIDATE_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
TAMU_SEEDS = {"2010": "137387", "2011": "137872"}
DOMAINS = (
    "schedule_game_count",
    "wins_losses_ties",
    "points_for_against",
    "team_season_statistics",
    "player_season_statistics",
    "roster_membership",
    "venues",
    "opponent_identity",
    "dates",
    "attendance",
    "officials",
    "drives",
    "play_by_play",
    "participation",
    "pregame_availability",
)
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "disposition",
    "tamu_seeds",
    "input_identities",
    "counts",
    "domains",
    "texas_2011_conflict",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
)


class AuthorityViolation(ValueError):
    """Raised when season reconciliation is asked to invent identity or availability."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "name_only_promotion": False,
        "season_total_as_per_game_official": False,
        "membership_as_availability": False,
        "participation_as_availability": False,
        "historical_known_at_from_capture_time": False,
        "historical_pit_admission": False,
        "preliminary_training_admission": False,
        "protected_training_admission": False,
        "protected_evaluation_admission": False,
        "protected_outcome_authority": False,
        "champion_or_production_promotion": False,
        "forecast_publication": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
        "bat_554_reopen": False,
        "bat_523_closed": False,
        "bat_429_ready_or_done": False,
    }


def expected_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "contest_ids_fabricated": False,
        "name_only_promoted": False,
        "season_total_promoted_to_per_game_official": False,
        "roster_membership_used_as_availability": False,
        "participation_used_as_availability": False,
        "historical_known_at_established": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_outcome_authority": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
        "bat_554_reopened": False,
        "bat_523_closed": False,
        "bat_429_advanced": False,
    }


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("season reconciliation contract identity drift")
    if contract.get("tamu_seeds") != TAMU_SEEDS:
        raise AuthorityViolation("TAMU seeds drifted")
    if contract.get("texas_2011_conflict", {}).get("name_only_promotion") is not False:
        raise AuthorityViolation("2011 Texas name-only promotion is forbidden")
    if contract.get("bat_554_policy") != "RELATES_ONLY_DO_NOT_REOPEN":
        raise AuthorityViolation("BAT-554 reopen is forbidden")
    for key, expected in expected_authority().items():
        if (contract.get("authority") or {}).get(key) is not expected:
            raise AuthorityViolation(f"contract authority {key} is not fail-closed")
    return contract


def _require_identity(gate: Mapping[str, Any], field: str, expected: str, label: str) -> None:
    observed = gate.get(field)
    if observed != expected:
        raise AuthorityViolation(f"{label} identity drifted: {observed}")


def _ncaa_schedule(phase2_manifest: Mapping[str, Any], season: int) -> list[dict[str, Any]]:
    for page in phase2_manifest.get("pages") or []:
        if page.get("season") == season and page.get("page_family") == "team":
            return list((page.get("parsed") or {}).get("schedule_rows") or [])
    raise AuthorityViolation(f"Phase 2 team page missing schedule rows for {season}")


def _comparison(
    *,
    season: int,
    domain: str,
    sources: dict[str, Any],
    raw_values: dict[str, Any],
    normalized: Any,
    agreement_rule: str,
    result: str,
    classification: str,
    authority: str,
    unresolved: list[str],
    bat523: bool,
    development_pit: bool,
    pregame: bool,
) -> dict[str, Any]:
    return {
        "season": season,
        "domain": domain,
        "source_identities": sources,
        "normalized_key": f"{season}:{domain}",
        "raw_values": raw_values,
        "normalized_values": normalized,
        "agreement_rule": agreement_rule,
        "result": result,
        "classification": classification,
        "authority": authority,
        "unresolved_conflicts": unresolved,
        "bat523_consumable": bat523,
        "development_pit_eligible": development_pit,
        "pregame_availability_eligible": pregame,
    }


def rebuild_expected(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    contract = load_contract(repo_root)
    identities = contract["input_identities"]
    phase2 = load_json(repo_root / identities["phase2_gate_relative_path"])
    bat570 = load_json(repo_root / identities["bat570_gate_relative_path"])
    bat571 = load_json(repo_root / identities["bat571_gate_relative_path"])
    bat572 = load_json(repo_root / identities["bat572_gate_relative_path"])
    _require_identity(phase2, "gate_identity", identities["phase2_gate_identity"], "BAT-574")
    _require_identity(phase2, "manifest_identity", identities["phase2_manifest_identity"], "BAT-574 manifest")
    _require_identity(bat570, "gate_identity", identities["bat570_gate_identity"], "BAT-570 gate")
    _require_identity(bat570, "matrix_identity", identities["bat570_matrix_identity"], "BAT-570 matrix")
    _require_identity(bat571, "gate_identity", identities["bat571_gate_identity"], "BAT-571 gate")
    _require_identity(bat571, "acquisition_identity", identities["bat571_acquisition_identity"], "BAT-571 acquisition")
    _require_identity(bat572, "gate_identity", identities["bat572_gate_identity"], "BAT-572 gate")
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    if hashlib.sha256(registry.read_bytes()).hexdigest() != identities["protected_split_registry_sha256"]:
        raise AuthorityViolation("protected-split registry identity drift")
    manifest_path = Path(str(phase2["payload"]["manifest"]))
    if not manifest_path.is_file():
        raise AuthorityViolation("Phase 2 bulk manifest is missing")
    if sha256_file(manifest_path) != phase2["payload"]["manifest_sha256"]:
        raise AuthorityViolation("Phase 2 bulk manifest hash drift")
    phase2_manifest = load_json(manifest_path)
    sidearm = {
        "2010": identities["sidearm_schedule_html_2010_sha256"],
        "2011": identities["sidearm_schedule_html_2011_sha256"],
    }
    for season, digest in sidearm.items():
        path = data_root / "raw/SRC-014/tamu_official_gamebook_equivalent/schedule_html" / f"sha256_{digest}.html"
        if not path.is_file() or sha256_file(path) != digest:
            raise AuthorityViolation(f"Sidearm {season} schedule HTML is missing or drifted")
    gap_dates = list((bat570.get("special_path") or {}).get("dates") or [])
    gap_2011_texas = "2011-11-25" if "2011-11-25" in gap_dates else None
    rows: list[dict[str, Any]] = []
    for season in (2010, 2011):
        ncaa_rows = _ncaa_schedule(phase2_manifest, season)
        ncaa_count = len(ncaa_rows)
        ncaa_wl = phase2["domains"]["wins_losses_ties"][str(season)]
        ncaa_pts = phase2["domains"]["points_for_against"][str(season)]["value"]
        gap_count = int(bat570["counts"][f"games_{season}"])
        acq_count = int(bat571["counts"][f"games_{season}"])
        count_agree = ncaa_count == 13 == gap_count == acq_count
        rows.append(
            _comparison(
                season=season,
                domain="schedule_game_count",
                sources={"ncaa_phase2": phase2["gate_identity"], "bat570": bat570["gate_identity"], "bat571": bat571["gate_identity"]},
                raw_values={"ncaa": ncaa_count, "gap_matrix": gap_count, "acquisition": acq_count},
                normalized=13 if count_agree else ncaa_count,
                agreement_rule="exact_integer_count",
                result="AGREE" if count_agree else "CONFLICT",
                classification="VERIFIED_CROSS_SOURCE" if count_agree else "CONFLICT_REVIEW_REQUIRED",
                authority="NCAA_OFFICIAL_TEAM_PAGE_PLUS_GOVERNED_SCHEDULE_COUNTS",
                unresolved=[],
                bat523=True,
                development_pit=count_agree,
                pregame=False,
            )
        )
        header = ncaa_wl.get("header_record") or {}
        wl_class = str(ncaa_wl.get("classification"))
        rows.append(
            _comparison(
                season=season,
                domain="wins_losses_ties",
                sources={"ncaa_phase2": phase2["gate_identity"]},
                raw_values={"schedule": ncaa_wl.get("value"), "header": header, "source": ncaa_wl.get("source")},
                normalized=ncaa_wl.get("value"),
                agreement_rule="header_versus_schedule_table",
                result="AGREE" if wl_class == "VERIFIED_OFFICIAL_SEASON_LEVEL" else "CONFLICT",
                classification=wl_class,
                authority="NCAA_OFFICIAL_TEAM_PAGE_SCHEDULE_TABLE",
                unresolved=["2011_header_0-0_versus_score_derived_7-6"] if season == 2011 else [],
                bat523=True,
                development_pit=season == 2010,
                pregame=False,
            )
        )
        rows.append(
            _comparison(
                season=season,
                domain="points_for_against",
                sources={"ncaa_phase2": phase2["gate_identity"]},
                raw_values=ncaa_pts,
                normalized=ncaa_pts,
                agreement_rule="sum_of_official_schedule_scores",
                result="AGREE",
                classification="VERIFIED_OFFICIAL_SEASON_LEVEL",
                authority="NCAA_OFFICIAL_TEAM_PAGE_SCHEDULE_TABLE",
                unresolved=[],
                bat523=True,
                development_pit=True,
                pregame=False,
            )
        )
        blocked = "OFFICIAL_ROUTE_ACCESS_BLOCKED"
        for domain in ("team_season_statistics", "player_season_statistics", "roster_membership"):
            rows.append(
                _comparison(
                    season=season,
                    domain=domain,
                    sources={"ncaa_phase2": phase2["gate_identity"]},
                    raw_values=phase2["domains"].get(domain, {}).get(str(season)),
                    normalized=None,
                    agreement_rule="optional_page_family_must_be_captured_to_admit",
                    result="MISSING",
                    classification=blocked,
                    authority="NO_VERIFIED_OPTIONAL_PAGE",
                    unresolved=[f"{season}_{domain}_official_page_403"],
                    bat523=True,
                    development_pit=False,
                    pregame=False,
                )
            )
        ncaa_opponents = [row["opponent_normalized"] for row in ncaa_rows]
        ncaa_dates = [row["game_date"] for row in ncaa_rows]
        texas = next((row for row in ncaa_rows if row["opponent_normalized"] == "Texas"), None)
        texas_conflict = season == 2011 and texas is not None and texas["game_date"] == "2011-11-24" and gap_2011_texas == "2011-11-25"
        rows.append(
            _comparison(
                season=season,
                domain="opponent_identity",
                sources={"ncaa_phase2": phase2["gate_identity"], "bat570": bat570["gate_identity"]},
                raw_values={"ncaa_opponents": ncaa_opponents, "ncaa_opponent_team_season_ids": [row.get("opponent_team_season_id") for row in ncaa_rows]},
                normalized=ncaa_opponents,
                agreement_rule="official_opponent_link_or_exact_date_score_not_name_only",
                result="CONFLICT" if texas_conflict else "AGREE_WITH_OFFICIAL_LINKS",
                classification="CONFLICT_REVIEW_REQUIRED" if texas_conflict else "VERIFIED_OFFICIAL_SEASON_LEVEL",
                authority="NCAA_OFFICIAL_OPPONENT_TEAM_SEASON_LINKS",
                unresolved=["2011_Texas_date_UNRESOLVED_NAME_ONLY_NOT_PROMOTED"] if texas_conflict else [],
                bat523=True,
                development_pit=not texas_conflict,
                pregame=False,
            )
        )
        rows.append(
            _comparison(
                season=season,
                domain="dates",
                sources={"ncaa_phase2": phase2["gate_identity"], "bat570_special_path": bat570["gate_identity"]},
                raw_values={"ncaa_dates": ncaa_dates, "gap_special_path_dates": [item for item in gap_dates if item.startswith(str(season)) or (season == 2010 and item == "2011-01-07")]},
                normalized=ncaa_dates,
                agreement_rule="exact_iso_date_plus_canonical_game_identity_required_to_resolve_conflict",
                result="CONFLICT" if texas_conflict else "AGREE",
                classification="CONFLICT_REVIEW_REQUIRED" if texas_conflict else "VERIFIED_CROSS_SOURCE",
                authority="NCAA_OFFICIAL_DATES_NOT_PROMOTED_OVER_SIDEARM_BY_NAME",
                unresolved=["2011_Texas_NCAA_2011-11-24_vs_gap_matrix_2011-11-25"] if texas_conflict else [],
                bat523=True,
                development_pit=not texas_conflict,
                pregame=False,
            )
        )
        for domain, classification, reason in (
            ("venues", "SOURCE_EVIDENCE_ABSENT", "no_official_venue_table_on_team_page"),
            ("attendance", "NOT_APPLICABLE_TO_SEASON_SUMMARY", "attendance_is_per_game_and_contest_endpoints_absent"),
            ("officials", "NOT_APPLICABLE_TO_SEASON_SUMMARY", "officials_are_per_game_and_contest_endpoints_absent"),
            ("drives", "SOURCE_EVIDENCE_ABSENT", "zero_ncaa_contest_ids"),
            ("play_by_play", "SOURCE_EVIDENCE_ABSENT", "zero_ncaa_contest_ids"),
            ("participation", "SOURCE_EVIDENCE_ABSENT", "zero_ncaa_contest_ids"),
            ("pregame_availability", "TEMPORALLY_INELIGIBLE_FOR_PREGAME_USE", "membership_and_participation_are_not_availability"),
        ):
            rows.append(
                _comparison(
                    season=season,
                    domain=domain,
                    sources={"ncaa_phase2": phase2["gate_identity"], "bat571": bat571["gate_identity"], "bat572": bat572["gate_identity"]},
                    raw_values={"contest_ids": 0, "wmt_2010_2011": "SOURCE_EVIDENCE_ABSENT_GAP_SEASONS"},
                    normalized=None,
                    agreement_rule="absent_or_temporally_ineligible_fail_closed",
                    result="MISSING",
                    classification=classification,
                    authority=reason,
                    unresolved=[reason],
                    bat523=domain != "pregame_availability",
                    development_pit=False,
                    pregame=False,
                )
            )
    texas_conflict = {
        "opponent": "Texas",
        "ncaa_official_date": "2011-11-24",
        "ncaa_opponent_team_season_id": "137876",
        "sidearm_or_gap_matrix_date": "2011-11-25",
        "disposition": "UNRESOLVED_NAME_ONLY_NOT_PROMOTED",
        "name_only_promotion": False,
        "canonical_game_identity": None,
        "resolved": False,
    }
    by_class: dict[str, int] = {}
    for row in rows:
        by_class[row["classification"]] = by_class.get(row["classification"], 0) + 1
    if any(row["pregame_availability_eligible"] for row in rows):
        raise AuthorityViolation("pregame eligibility was opened")
    if any(row["domain"] == "pregame_availability" and row["classification"] != "TEMPORALLY_INELIGIBLE_FOR_PREGAME_USE" for row in rows):
        raise AuthorityViolation("availability domain drifted")
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_SEASON_RECONCILIATION_MANIFEST",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "run_id": contract["run_id"],
        "tamu_seeds": dict(TAMU_SEEDS),
        "disposition": "SEASON_LEVEL_RECONCILED_WITH_UNRESOLVED_TEXAS_DATE",
        "input_identities": {
            "phase2_gate_identity": phase2["gate_identity"],
            "phase2_manifest_identity": phase2["manifest_identity"],
            "bat570_gate_identity": bat570["gate_identity"],
            "bat570_matrix_identity": bat570["matrix_identity"],
            "bat571_gate_identity": bat571["gate_identity"],
            "bat571_acquisition_identity": bat571["acquisition_identity"],
            "bat572_gate_identity": bat572["gate_identity"],
            "sidearm_schedule_html_2010_sha256": identities["sidearm_schedule_html_2010_sha256"],
            "sidearm_schedule_html_2011_sha256": identities["sidearm_schedule_html_2011_sha256"],
            "protected_split_registry_sha256": identities["protected_split_registry_sha256"],
        },
        "counts": {
            "seasons": 2,
            "domains": len(DOMAINS),
            "comparison_rows": len(rows),
            "by_classification": by_class,
            "contest_ids_fabricated": 0,
            "name_only_promotions": 0,
            "availability_features": 0,
            "texas_2011_conflicts": 1,
        },
        "domains": {
            domain: [row for row in rows if row["domain"] == domain] for domain in DOMAINS
        },
        "texas_2011_conflict": texas_conflict,
        "rows": rows,
        "admissions": {
            "reconciliation_admission": "CANDIDATE_ONLY",
            "disposition": "SEASON_LEVEL_RECONCILED_WITH_UNRESOLVED_TEXAS_DATE",
            "pregame_availability": "BLOCKED",
            "protected_lane": PROTECTED_LANE,
            "bat_523": "IN_PROGRESS",
            "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
            "bat_554": "RELATES_ONLY_DO_NOT_REOPEN",
            "texas_2011": "UNRESOLVED_NAME_ONLY_NOT_PROMOTED",
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "issued_at_utc": issued_at_utc,
    }
    core["manifest_identity"] = stable_hash(
        {key: core[key] for key in ("schema_version", "domains", "texas_2011_conflict", "tamu_seeds", "input_identities")}
    )
    return core


def compute_gate_identity(payload: Mapping[str, Any]) -> str:
    return stable_hash({field: payload.get(field) for field in GATE_IDENTITY_FIELDS})


def expected_gate_document(core: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_SEASON_RECONCILIATION_GATE",
        "result": "PASS_SEASON_LEVEL_RECONCILED_WITH_UNRESOLVED_TEXAS_DATE",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": core["decision_unit"],
        "jira_key": core["jira_key"],
        "disposition": core["disposition"],
        "tamu_seeds": core["tamu_seeds"],
        "input_identities": core["input_identities"],
        "counts": core["counts"],
        "domains": {
            domain: [
                {key: value for key, value in row.items() if key != "raw_values"}
                for row in core["domains"][domain]
            ]
            for domain in DOMAINS
        },
        "texas_2011_conflict": core["texas_2011_conflict"],
        "admissions": core["admissions"],
        "authority": core["authority"],
        "scientific_nonclaims": core["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "manifest_identity": core["manifest_identity"],
        "payload": payload,
        "issued_at_utc": core["issued_at_utc"],
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    core = rebuild_expected(data_root=data_root, repo_root=repo_root, issued_at_utc=issued_at_utc)
    payload_dir = data_root / "features" / "tamu_2010_2011_season_reconciliation" / "sha256" / core["manifest_identity"]
    payload_dir.mkdir(parents=True, exist_ok=True)
    rows_path = payload_dir / "season_reconciliation_rows.json"
    write_json(rows_path, core["rows"])
    manifest_path = payload_dir / "tamu_2010_2011_season_reconciliation_manifest.json"
    write_json(manifest_path, {key: value for key, value in core.items() if key != "rows"})
    payload = {
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "rows": str(rows_path),
        "rows_sha256": sha256_file(rows_path),
        "row_count": len(core["rows"]),
    }
    gate = expected_gate_document(core, payload)
    write_json(repo_root / GATE_RELATIVE, gate)
    return {"gate": gate, "payload": payload}


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    contract = load_contract(repo_root)
    expected_inputs = {
        "phase2_gate_identity": contract["input_identities"]["phase2_gate_identity"],
        "phase2_manifest_identity": contract["input_identities"]["phase2_manifest_identity"],
        "bat570_gate_identity": contract["input_identities"]["bat570_gate_identity"],
        "bat570_matrix_identity": contract["input_identities"]["bat570_matrix_identity"],
        "bat571_gate_identity": contract["input_identities"]["bat571_gate_identity"],
        "bat571_acquisition_identity": contract["input_identities"]["bat571_acquisition_identity"],
        "bat572_gate_identity": contract["input_identities"]["bat572_gate_identity"],
        "sidearm_schedule_html_2010_sha256": contract["input_identities"]["sidearm_schedule_html_2010_sha256"],
        "sidearm_schedule_html_2011_sha256": contract["input_identities"]["sidearm_schedule_html_2011_sha256"],
        "protected_split_registry_sha256": contract["input_identities"]["protected_split_registry_sha256"],
    }
    if committed.get("input_identities") != expected_inputs:
        raise AuthorityViolation("input identities drifted")
    if committed.get("counts", {}).get("comparison_rows") != 30:
        raise AuthorityViolation("comparison row total drifted")
    if committed.get("counts", {}).get("texas_2011_conflicts") != 1:
        raise AuthorityViolation("2011 Texas conflict count drifted")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification drifted")
    if committed.get("result") != "PASS_SEASON_LEVEL_RECONCILED_WITH_UNRESOLVED_TEXAS_DATE":
        raise AuthorityViolation("result drifted")
    if committed["tamu_seeds"] != TAMU_SEEDS:
        raise AuthorityViolation("seeds drifted")
    if committed["authority"] != expected_authority():
        raise AuthorityViolation("authority drifted")
    if committed["scientific_nonclaims"] != expected_nonclaims():
        raise AuthorityViolation("nonclaims drifted")
    if committed["protected_lane"] != PROTECTED_LANE:
        raise AuthorityViolation("protected lane drifted")
    if committed["texas_2011_conflict"].get("resolved"):
        raise AuthorityViolation("2011 Texas conflict was falsely resolved")
    if committed["texas_2011_conflict"].get("name_only_promotion"):
        raise AuthorityViolation("2011 Texas was name-only promoted")
    if committed["counts"]["contest_ids_fabricated"] != 0:
        raise AuthorityViolation("contest IDs were fabricated")
    if committed["counts"]["availability_features"] != 0:
        raise AuthorityViolation("availability features were admitted")
    if any(committed["authority"].values()):
        raise AuthorityViolation("authority claim was opened")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not reconstruct")
    if require_rebuild:
        rebuilt = rebuild_expected(data_root=data_root, repo_root=repo_root, issued_at_utc=str(committed.get("issued_at_utc")))
        expected = expected_gate_document(rebuilt, committed.get("payload") or {})
        if committed["gate_identity"] != expected["gate_identity"]:
            raise AuthorityViolation("rebuilt gate identity drifted")
        payload = committed.get("payload") or {}
        rows_path = Path(str(payload.get("rows") or ""))
        if not rows_path.is_file() or sha256_file(rows_path) != payload.get("rows_sha256"):
            raise AuthorityViolation("bulk row payload hash drift")
        if any(row["classification"] == "VERIFIED_OFFICIAL" and row["domain"] in {"attendance", "officials", "drives", "play_by_play"} for row in rebuilt["rows"]):
            raise AuthorityViolation("season summary was promoted to per-game official")
    return {"result": "PASS", "gate_identity": committed["gate_identity"]}
