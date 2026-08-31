"""Fail-closed tests for the Week 1 2026 coverage and adequacy gate."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from aggie_analytics.data.week1_2026_feature_coverage_adequacy import (
    ABSTAIN_MISSING,
    ABSTAIN_UNSUPPORTED,
    CONTRACT_RELATIVE,
    PARTIAL,
    QUARANTINED,
    READY,
    Week1AdequacyViolation,
    build_adequacy_rows,
    compare_contest_to_national_distribution,
    summarize,
    validate_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

DOMAIN_DEFAULTS = {
    "TEAM_STRENGTH_PRIOR": "SOURCE_EVIDENCE_ABSENT",
    "WEEK_ZERO_CURRENT_RESULT": "SOURCE_EVIDENCE_ABSENT",
    "CURRENT_RANKING": "CANDIDATE_ONLY_NOT_CONSUMED",
    "CONFERENCE_AND_SUBDIVISION": "ADMITTED_PROSPECTIVE_PREKICKOFF",
    "VENUE_AND_SITE": "ADMITTED_PROSPECTIVE_PREKICKOFF",
    "WEATHER_VINTAGE": "CANDIDATE_ONLY_NOT_CONSUMED",
    "ROSTER_MEMBERSHIP": "SOURCE_EVIDENCE_ABSENT",
    "PREGAME_AVAILABILITY": "SOURCE_EVIDENCE_ABSENT",
}


def spine_row(
    *,
    contest_id: str,
    orientation: str,
    team_id: str,
    display_name: str,
    canonical: str | None = "SRC-002:TEAM:1",
    kickoff: str | None = "2026-09-05T23:00:00Z",
    admitted: bool = True,
) -> dict:
    return {
        "row_identity": f"row-{contest_id}-{orientation}",
        "contest_identity": f"identity-{contest_id}",
        "ncaa_contest_id": contest_id,
        "requested_game_date": "2026-09-05",
        "kickoff_utc_conservative_lower_bound": kickoff,
        "kickoff_time_state": "KICKOFF_TIME_PUBLISHED",
        "contest_disposition": "ADMITTED_MODEL_ELIGIBLE"
        if admitted
        else "UNSUPPORTED_ENTITY",
        "spine_row_state": "SPINE_ROW_ADMITTED"
        if admitted
        else "SPINE_ROW_UNSUPPORTED_ENTITY",
        "orientation": orientation,
        "is_neutral_site": False,
        "source_team_id": team_id,
        "source_display_name": display_name,
        "canonical_team_id": canonical,
        "subdivision": "FBS",
        "conference_name": "SEC",
        "ranked_state": "RANKED" if orientation == "HOME" else "UNRANKED",
        "availability_feature_count": 0,
    }


def cells_for(row: dict, overrides: dict | None = None) -> list[dict]:
    dispositions = {**DOMAIN_DEFAULTS, **(overrides or {})}
    return [
        {
            "row_identity": row["row_identity"],
            "ncaa_contest_id": row["ncaa_contest_id"],
            "source_team_id": row["source_team_id"],
            "canonical_team_id": row["canonical_team_id"],
            "orientation": row["orientation"],
            "domain": domain,
            "value": None
            if disposition == "SOURCE_EVIDENCE_ABSENT"
            else {"present": True},
            "admission_disposition": disposition,
            "missingness_reason": "ABSENT"
            if disposition == "SOURCE_EVIDENCE_ABSENT"
            else None,
        }
        for domain, disposition in dispositions.items()
    ]


def contract() -> dict:
    return validate_contract(
        json.loads((REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig"))
    )


def population(overrides: dict | None = None, **row_kwargs):
    away = spine_row(
        contest_id="700001",
        orientation="AWAY",
        team_id="600001",
        display_name="Missouri St.",
        **row_kwargs,
    )
    home = spine_row(
        contest_id="700001",
        orientation="HOME",
        team_id="600002",
        display_name="Texas A&M",
        **row_kwargs,
    )
    rows = [away, home]
    cells = cells_for(away, overrides) + cells_for(home, overrides)
    return rows, cells


class ContractProtectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig")
        )

    def test_published_contract_is_accepted(self) -> None:
        self.assertEqual(validate_contract(self.contract)["jira_key"], "BAT-678")

    def test_a_forecast_cannot_be_authorized(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["authority"]["forecast_produced"] = True
        with self.assertRaises(Week1AdequacyViolation):
            validate_contract(broken)

    def test_model_promotion_cannot_be_authorized(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["authority"]["champion_or_production_promotion"] = True
        with self.assertRaises(Week1AdequacyViolation):
            validate_contract(broken)

    def test_post_hoc_candidate_insertion_is_refused(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["sources"]["frozen_candidates"]["post_hoc_candidate_insertion"] = True
        with self.assertRaises(Week1AdequacyViolation):
            validate_contract(broken)

    def test_checkpoints_cannot_be_closed(self) -> None:
        for field in ("t_minus_24h_state", "t_minus_90m_state"):
            broken = copy.deepcopy(self.contract)
            broken["checkpoints"][field] = "CLOSED"
            with self.assertRaises(Week1AdequacyViolation):
                validate_contract(broken)

    def test_early_checkpoint_execution_is_refused(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["checkpoints"]["executed_early"] = True
        with self.assertRaises(Week1AdequacyViolation):
            validate_contract(broken)

    def test_pregame_result_access_is_refused(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["checkpoints"]["pregame_result_access"] = True
        with self.assertRaises(Week1AdequacyViolation):
            validate_contract(broken)

    def test_tamu_specific_adjustment_is_refused(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["tamu_policy"]["tamu_specific_adjustment_applied"] = True
        with self.assertRaises(Week1AdequacyViolation):
            validate_contract(broken)

    def test_a_candidate_cannot_require_an_undeclared_domain(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["candidate_feature_requirements"][0]["required_domains"] = [
            "INVENTED_DOMAIN"
        ]
        with self.assertRaises(Week1AdequacyViolation):
            validate_contract(broken)


class AdequacyTests(unittest.TestCase):
    def test_a_candidate_without_required_features_is_ready_when_identity_resolves(
        self,
    ) -> None:
        rows, cells = population()
        _, candidates = build_adequacy_rows(contract=contract(), rows=rows, cells=cells)
        base = next(
            row for row in candidates if row["candidate_id"] == "national_base_rate"
        )
        self.assertEqual(base["adequacy_state"], READY)
        self.assertEqual(base["missing_required_count"], 0)

    def test_a_candidate_missing_every_required_domain_abstains(self) -> None:
        rows, cells = population()
        _, candidates = build_adequacy_rows(contract=contract(), rows=rows, cells=cells)
        logistic = next(
            row for row in candidates if row["candidate_id"] == "national_logistic_l2"
        )
        self.assertEqual(logistic["adequacy_state"], PARTIAL)
        self.assertIn("TEAM_STRENGTH_PRIOR", logistic["missing_required_domains"])
        self.assertNotIn("VENUE_AND_SITE", logistic["missing_required_domains"])

    def test_a_candidate_with_no_admitted_required_domain_abstains_outright(
        self,
    ) -> None:
        rows, cells = population(overrides={"VENUE_AND_SITE": "SOURCE_EVIDENCE_ABSENT"})
        _, candidates = build_adequacy_rows(contract=contract(), rows=rows, cells=cells)
        prior = next(row for row in candidates if row["candidate_id"] == "prior_only")
        self.assertEqual(prior["adequacy_state"], ABSTAIN_MISSING)

    def test_a_missing_required_domain_can_never_be_ready(self) -> None:
        rows, cells = population()
        contests, candidates = build_adequacy_rows(
            contract=contract(), rows=rows, cells=cells
        )
        for row in candidates:
            if row["missing_required_count"]:
                self.assertNotEqual(row["adequacy_state"], READY)
        self.assertEqual(contests[0]["adequacy_state"], PARTIAL)

    def test_an_unsupported_entity_abstains_for_every_candidate(self) -> None:
        rows, cells = population(canonical=None, admitted=False)
        contests, candidates = build_adequacy_rows(
            contract=contract(), rows=rows, cells=cells
        )
        self.assertEqual(contests[0]["adequacy_state"], ABSTAIN_UNSUPPORTED)
        self.assertEqual(
            {row["adequacy_state"] for row in candidates}, {ABSTAIN_UNSUPPORTED}
        )

    def test_a_conflicted_domain_quarantines_the_contest(self) -> None:
        rows, cells = population(overrides={"CURRENT_RANKING": "QUARANTINED_CONFLICT"})
        contests, candidates = build_adequacy_rows(
            contract=contract(), rows=rows, cells=cells
        )
        self.assertEqual(contests[0]["adequacy_state"], QUARANTINED)
        self.assertEqual({row["adequacy_state"] for row in candidates}, {QUARANTINED})

    def test_an_unresolved_kickoff_bound_abstains(self) -> None:
        rows, cells = population(kickoff=None)
        contests, _ = build_adequacy_rows(contract=contract(), rows=rows, cells=cells)
        self.assertEqual(contests[0]["adequacy_state"], ABSTAIN_MISSING)

    def test_a_domain_admitted_for_only_one_team_is_not_admitted_for_the_contest(
        self,
    ) -> None:
        away = spine_row(
            contest_id="700001",
            orientation="AWAY",
            team_id="600001",
            display_name="Missouri St.",
        )
        home = spine_row(
            contest_id="700001",
            orientation="HOME",
            team_id="600002",
            display_name="Texas A&M",
        )
        cells = cells_for(away) + cells_for(
            home, {"CONFERENCE_AND_SUBDIVISION": "SOURCE_EVIDENCE_ABSENT"}
        )
        _, candidates = build_adequacy_rows(
            contract=contract(), rows=[away, home], cells=cells
        )
        logistic = next(
            row for row in candidates if row["candidate_id"] == "national_logistic_l2"
        )
        self.assertIn(
            "CONFERENCE_AND_SUBDIVISION", logistic["missing_required_domains"]
        )

    def test_candidate_counts_reconcile(self) -> None:
        rows, cells = population()
        _, candidates = build_adequacy_rows(contract=contract(), rows=rows, cells=cells)
        for row in candidates:
            self.assertEqual(
                row["admitted_required_count"] + row["missing_required_count"],
                row["required_feature_count"],
            )

    def test_no_row_claims_a_forecast(self) -> None:
        rows, cells = population()
        contests, candidates = build_adequacy_rows(
            contract=contract(), rows=rows, cells=cells
        )
        for row in contests + candidates:
            self.assertFalse(row["forecast_produced"])

    def test_summary_counts_every_candidate_row(self) -> None:
        rows, cells = population()
        contests, candidates = build_adequacy_rows(
            contract=contract(), rows=rows, cells=cells
        )
        summary = summarize(contests, candidates, rows)
        self.assertEqual(summary["candidate_row_count"], len(candidates))
        self.assertEqual(
            sum(summary["contest_adequacy_counts"].values()), summary["contest_count"]
        )

    def test_focus_contest_is_reported_without_correction(self) -> None:
        rows, cells = population()
        contests, candidates = build_adequacy_rows(
            contract=contract(), rows=rows, cells=cells
        )
        report = compare_contest_to_national_distribution(
            contest_row=contests[0], contest_rows=contests, candidate_rows=candidates
        )
        self.assertFalse(report["custom_correction_applied"])
        self.assertFalse(report["hardcoded_feature_applied"])
        self.assertEqual(report["adequacy_state"], contests[0]["adequacy_state"])
        self.assertEqual(len(report["candidate_rows"]), len(candidates))

    def test_a_contest_without_two_rows_is_refused(self) -> None:
        rows, cells = population()
        with self.assertRaises(Week1AdequacyViolation):
            build_adequacy_rows(contract=contract(), rows=rows[:1], cells=cells)


if __name__ == "__main__":
    unittest.main()
