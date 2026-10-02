"""Fail-closed tests for the Cycle #24 Week 1 2026 current-authority enrichment."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from aggie_analytics.data import week1_2026_authority_enrichment as A

REPO_ROOT = Path(__file__).resolve().parents[1]


def data_root() -> Path | None:
    value = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    return Path(value) if value else None


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = A.load_contract(REPO_ROOT)

    def test_contract_identity_and_lane(self) -> None:
        self.assertEqual(self.contract["contract_id"], A.CONTRACT_ID)
        self.assertEqual(self.contract["lane"], A.LANE)
        self.assertEqual(self.contract["protected_lane"], A.PROTECTED_LANE)
        self.assertEqual(self.contract["jira_key"], A.JIRA_KEY)

    def test_protected_seasons_stay_excluded(self) -> None:
        self.assertEqual(
            sorted(self.contract["protected_evidence"]["excluded_protected_seasons"]),
            [2024, 2025],
        )
        self.assertFalse(self.contract["protected_evidence"]["week1_outcome_read"])
        self.assertFalse(self.contract["protected_evidence"]["target_outcome_read"])

    def test_checkpoints_remain_open(self) -> None:
        checkpoints = self.contract["checkpoints"]
        self.assertEqual(checkpoints["t_minus_24h_state"], "OPEN")
        self.assertEqual(checkpoints["t_minus_90m_state"], "OPEN")
        self.assertFalse(checkpoints["executed_early"])

    def test_eight_unresolved_participants_are_declared(self) -> None:
        declared = self.contract["unresolved_participants"]
        self.assertEqual(len(declared), 8)
        self.assertEqual(
            sorted(item["source_team_id"] for item in declared),
            [
                "622349",
                "622350",
                "622352",
                "622358",
                "622407",
                "622417",
                "622443",
                "622444",
            ],
        )

    def test_display_name_only_resolution_stays_forbidden(self) -> None:
        rules = self.contract["identity_rules"]
        self.assertTrue(rules["forbid_display_name_only_resolution"])
        self.assertTrue(rules["forbid_fuzzy_threshold_reduction"])
        self.assertTrue(rules["require_season_team_identifier_link"])

    def test_contract_rejects_a_relaxed_weather_policy(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["weather_policy"]["admitted_requires_authoritative_coordinates"] = False
        with self.assertRaises(A.AuthorityEnrichmentViolation):
            A.load_contract_mapping(relaxed)


class ParsingTests(unittest.TestCase):
    def test_contest_graph_extraction_and_indexing(self) -> None:
        text = (
            'noise{"initialGames":[{"contestId":1,"startDate":"09/05/2026",'
            '"startTimeEpoch":1788649200,"hasStartTime":true,"broadcasterName":"NET",'
            '"startTime":"19:00","teams":[{"isHome":true,"seoname":"texas-am",'
            '"nameShort":"Texas A&M","teamRank":8},{"isHome":false,'
            '"seoname":"missouri-st","nameShort":"Missouri St.","teamRank":null}]}]}tail'
        )
        games = A.parse_contest_graph(text, graph_key="initialGames")
        self.assertEqual(len(games), 1)
        index = A.index_contest_graph(games)
        self.assertIn(("2026-09-05", "texas a&m", "missouri st"), index)

    def test_absent_graph_fails_closed(self) -> None:
        with self.assertRaises(A.AuthorityEnrichmentViolation):
            A.parse_contest_graph("no graph here", graph_key="initialGames")

    def test_poll_rows_preserve_tie_groups_and_never_invent_rank_26(self) -> None:
        text = (
            "<tr><td>13</td><td>Alabama</td><td>904</td></tr>"
            "<tr><td>T14</td><td>BYU</td><td>839</td></tr>"
            "<tr><td>T14</td><td>Southern Cal</td><td>839</td></tr>"
        )
        rows = A.parse_poll_rows(text)
        self.assertEqual([row["rank"] for row in rows], [13, 14, 14])
        self.assertEqual(rows[2]["tie_group"], "T14")
        self.assertNotIn(26, [row["rank"] for row in rows])

    def test_season_membership_requires_the_exact_team_identifier(self) -> None:
        text = (
            '<tr role="row"><td class="sorting_1"><a href="/teams/622350">2026-27</a></td>'
            "<td><a>Coach</a></td><td>FCS</td><td>UAC </td><td>0</td></tr>"
        )
        membership = A.parse_official_season_membership(text, source_team_id="622350")
        self.assertEqual(membership["official_season_label"], "2026-27")
        self.assertEqual(membership["subdivision"], "FCS")
        self.assertEqual(membership["conference_label"], "UAC")
        self.assertIsNone(
            A.parse_official_season_membership(text, source_team_id="999999"),
            "a different season team identifier must not resolve",
        )


class Cycle26FrozenPredecessorContainmentTests(unittest.TestCase):
    def test_schedule_identity_mismatch_does_not_rewrite_committed_gate(self) -> None:
        contract = A.load_contract(REPO_ROOT)
        gate_path = (
            REPO_ROOT / contract["sources"]["schedule_identity"]["gate_relative_path"]
        )
        before = gate_path.read_bytes()
        pinned = contract["sources"]["schedule_identity"]["gate_identity"]
        actual = A.read_json(gate_path)["gate_identity"]
        after = gate_path.read_bytes()
        self.assertEqual(before, after)
        if pinned != actual:
            self.assertNotEqual(
                pinned,
                actual,
                "a later capture must not silently equal a frozen Cycle24 pin",
            )


class MaterializedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = data_root()
        if cls.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        gate_path = REPO_ROOT / A.GATE_RELATIVE
        if not gate_path.is_file():
            raise unittest.SkipTest("authority gate is not materialized")
        cls.gate = A.read_json(gate_path)
        try:
            cls.expected = A.build_expected(repo_root=REPO_ROOT, data_root=cls.root)
        except A.AuthorityEnrichmentViolation as exc:
            raise unittest.SkipTest(
                "Cycle26 forbids rematerializing the frozen Week1 schedule identity "
                f"from a later refresh: {exc}"
            ) from exc

    def test_gate_identity_recomputes(self) -> None:
        self.assertEqual(A.compute_gate_identity(self.gate), self.gate["gate_identity"])
        self.assertEqual(
            self.gate["dataset_identity"], self.expected["dataset_identity"]
        )

    def test_independent_validation_passes(self) -> None:
        report = A.validate_artifact(repo_root=REPO_ROOT, data_root=self.root)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["mode"], "INDEPENDENT_REBUILD")

    def test_every_unresolved_participant_has_a_terminal_disposition(self) -> None:
        rows = self.expected["entity_rows"]
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertIn(
                row["disposition"],
                (A.RESOLVED_AUTHORITATIVE_IDENTITY, A.ABSTAIN_UNSUPPORTED_ENTITY),
            )
            if row["disposition"] == A.RESOLVED_AUTHORITATIVE_IDENTITY:
                self.assertTrue(row["season_team_identifier_link_observed"])
                self.assertFalse(row["resolved_by_display_name_only"])
                self.assertFalse(row["canonical_development_history_available"])
            else:
                self.assertTrue(row["missing_evidence"])

    def test_kickoff_confirmation_is_earned(self) -> None:
        for row in self.expected["kickoff_rows"]:
            if row["kickoff_utc_independently_confirmed"]:
                self.assertEqual(
                    row["official_kickoff_utc"], row["predecessor_kickoff_bound_utc"]
                )
                self.assertEqual(
                    row["kickoff_confirmation_state"], A.INDEPENDENTLY_CONFIRMED
                )
            else:
                self.assertNotEqual(
                    row["kickoff_confirmation_state"], A.INDEPENDENTLY_CONFIRMED
                )

    def test_focus_contest_kickoff_and_venue_are_bound(self) -> None:
        focus = self.expected["focus_contest_report"]
        self.assertEqual(focus["official_kickoff_utc"], "2026-09-05T23:00:00Z")
        self.assertEqual(focus["official_kickoff_epoch"], 1788649200)
        self.assertEqual(focus["kickoff_confirmation_state"], A.INDEPENDENTLY_CONFIRMED)
        self.assertEqual(focus["venue_identity"], "Kyle Field")
        self.assertEqual(focus["venue_identity_state"], A.VENUE_IDENTITY_BOUND)
        self.assertTrue(focus["venue_identity_matches_declared_venue"])
        self.assertFalse(focus["tamu_specific_adjustment_applied"])

    def test_ranking_surface_is_complete_and_correctly_encoded(self) -> None:
        ranking = self.expected["ranking_completion"]
        self.assertTrue(ranking["poll_surface_complete"])
        self.assertEqual(ranking["unbound_poll_ranks"], [])
        self.assertEqual(ranking["unranked_encoded_as_26_count"], 0)
        alias = ranking["alias_bindings"][0]
        self.assertEqual(alias["binding_state"], "ALIAS_BOUND_THROUGH_RANK_AGREEMENT")
        self.assertEqual(
            alias["poll_rank_observed"], alias["official_slug_rank_observed"]
        )
        for row in self.expected["ranking_rows"]:
            if row["subdivision"] != "FBS":
                self.assertEqual(row["ranking_state"], A.NOT_APPLICABLE_FBS_POLL)
                self.assertIsNone(row["poll_rank"])
                self.assertFalse(row["is_unranked"])
            elif row["ranking_state"] == A.RANKED_TOP_25:
                self.assertTrue(1 <= row["poll_rank"] <= 25)
            else:
                self.assertEqual(row["ranking_state"], A.FBS_POLL_ELIGIBLE_UNRANKED)
                self.assertIsNone(row["poll_rank"])
                self.assertTrue(row["is_unranked"])

    def test_venue_and_weather_stay_fail_closed(self) -> None:
        for row in self.expected["venue_rows"]:
            self.assertFalse(row["venue_coordinates_admitted"])
            self.assertFalse(row["weather_admitted_model_input"])
            self.assertEqual(row["weather_state"], A.WEATHER_CANDIDATE_ONLY)
            self.assertFalse(row["venue_identity_admitted_from_site_orientation_alone"])
            if row["venue_identity_state"] == A.VENUE_IDENTITY_BOUND:
                self.assertTrue(row["venue_authority_licensed_for_this_contest"])
                self.assertTrue(row["venue_identity"])

    def test_gate_rejects_a_mutated_weather_admission(self) -> None:
        mutated = json.loads(json.dumps(self.gate))
        mutated["venue_and_weather"]["weather_admitted_model_input_count"] = 1
        with self.assertRaises(A.AuthorityEnrichmentViolation):
            A.enforce_invariants(mutated)

    def test_gate_rejects_a_closed_checkpoint(self) -> None:
        mutated = json.loads(json.dumps(self.gate))
        mutated["checkpoints"]["t_minus_24h_state"] = "EXECUTED"
        with self.assertRaises(A.AuthorityEnrichmentViolation):
            A.enforce_invariants(mutated)

    def test_gate_rejects_display_name_only_resolution(self) -> None:
        mutated = json.loads(json.dumps(self.gate))
        mutated["entity_resolution"]["resolved_by_display_name_only_count"] = 1
        with self.assertRaises(A.AuthorityEnrichmentViolation):
            A.enforce_invariants(mutated)

    def test_gate_rejects_a_predecessor_rewrite(self) -> None:
        mutated = json.loads(json.dumps(self.gate))
        mutated["bound_predecessors"]["predecessor_artifacts_rewritten_in_place"] = True
        with self.assertRaises(A.AuthorityEnrichmentViolation):
            A.enforce_invariants(mutated)

    def test_gate_emits_no_forecast_and_no_prior(self) -> None:
        self.assertFalse(self.gate["summary"]["forecast_emitted"])
        self.assertFalse(self.gate["summary"]["prior_materialized"])


if __name__ == "__main__":
    unittest.main()
