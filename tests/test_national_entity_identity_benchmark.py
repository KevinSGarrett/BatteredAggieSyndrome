"""Focused and tamper coverage for the national entity-identity benchmark."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from aggie_analytics.data.national_entity_identity_benchmark import (
    EntityBenchmarkViolation,
    SeasonScope,
    apply_acceptance_rules,
    build_artifact,
    comparable_official_seasons,
    derive_spine_season_records,
    parse_organization_directory,
    parse_season_record_series,
    payload_identity,
    resolve_organization,
    score_candidates,
    sha256_of,
    shift_series,
)

CONTRACT = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "configs/national_entity_identity_benchmark_contract.json"
    ).read_text(encoding="utf-8-sig")
)

DIRECTORY_HTML = """
<select id="org_id_select" name="org_id">
  <option value="657">Southern California</option>
  <option value="655">Southeastern La.</option>
  <option value="30">South Carolina &amp; Co.</option>
</select>
"""

HISTORY_HTML = """
<table>
<tr><th>Year</th><th>Head Coaches</th><th>Division</th><th>Conference</th>
    <th>Wins</th><th>Losses</th><th>Ties</th><th>WL%</th></tr>
<tr><td><a href="/teams/606032">2023-24</a></td><td>Coach</td><td>FBS</td><td>Pac-12</td>
    <td>8</td><td>5</td><td>0</td><td>.615</td></tr>
<tr><td><a href="/teams/544590">2022-23</a></td><td>Coach</td><td>FBS</td><td>Pac-12</td>
    <td>11</td><td>3</td><td>0</td><td>.786</td></tr>
<tr><td><a href="/teams/500000">2005-06</a></td><td>Coach</td><td>FBS</td><td>Pac-12</td>
    <td>0</td><td>0</td><td>0</td><td>.000</td></tr>
</table>
"""


def label_rows(team: str, records: dict[int, tuple[int, int, int]]) -> list[dict]:
    rows: list[dict] = []
    for season, (wins, losses, ties) in records.items():
        for _ in range(wins):
            rows.append(
                {"canonical_team_id": team, "season": season, "label_win": True, "label_tie": False}
            )
        for _ in range(losses):
            rows.append(
                {"canonical_team_id": team, "season": season, "label_win": False, "label_tie": False}
            )
        for _ in range(ties):
            rows.append(
                {"canonical_team_id": team, "season": season, "label_win": False, "label_tie": True}
            )
    return rows


def series_from(records: dict[int, tuple[int, int, int]]) -> list[dict]:
    return [
        {
            "conference": "C",
            "division": "FBS",
            "losses": losses,
            "official_academic_year": f"{season}-{str(season + 1)[2:]}",
            "season": season,
            "team_season_id": None,
            "ties": ties,
            "wins": wins,
        }
        for season, (wins, losses, ties) in sorted(records.items())
    ]


LONG_RECORD = {season: (season % 9 + 3, 12 - (season % 9 + 3), 0) for season in range(2004, 2024)}


class ParsingTests(unittest.TestCase):
    def test_directory_parses_official_labels_to_identifiers(self) -> None:
        directory = parse_organization_directory(DIRECTORY_HTML)
        self.assertEqual(directory["Southern California"], 657)
        self.assertEqual(directory["Southeastern La."], 655)
        self.assertEqual(directory["South Carolina & Co."], 30)

    def test_missing_directory_fails_closed(self) -> None:
        with self.assertRaises(EntityBenchmarkViolation):
            parse_organization_directory("<html><body>no select</body></html>")

    def test_history_parses_season_records_and_team_links(self) -> None:
        series = parse_season_record_series(HISTORY_HTML)
        self.assertEqual([entry["season"] for entry in series], [2005, 2022, 2023])
        self.assertEqual(series[-1]["wins"], 8)
        self.assertEqual(series[-1]["team_season_id"], "606032")

    def test_zero_game_rows_are_not_comparable(self) -> None:
        scope = SeasonScope.from_contract(CONTRACT)
        comparable = comparable_official_seasons(parse_season_record_series(HISTORY_HTML), scope)
        self.assertNotIn(2005, comparable)
        self.assertEqual(sorted(comparable), [2022, 2023])


class ScopeTests(unittest.TestCase):
    def test_sealed_seasons_are_never_comparable(self) -> None:
        scope = SeasonScope.from_contract(CONTRACT)
        self.assertFalse(scope.admits(2024))
        self.assertFalse(scope.admits(2025))
        self.assertTrue(scope.admits(2023))

    def test_sealed_seasons_are_dropped_from_comparison(self) -> None:
        scope = SeasonScope.from_contract(CONTRACT)
        series = series_from({2023: (8, 5, 0), 2024: (7, 6, 0), 2025: (9, 4, 0)})
        self.assertEqual(sorted(comparable_official_seasons(series, scope)), [2023])


class ResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spine = derive_spine_season_records(label_rows("TEAM:A", LONG_RECORD))

    def test_exact_long_history_resolves(self) -> None:
        verdict = resolve_organization(
            official_series=series_from(LONG_RECORD),
            spine_records=self.spine,
            contract=CONTRACT,
        )
        self.assertEqual(verdict["canonical_team_id"], "TEAM:A")
        self.assertEqual(verdict["tier_id"], "PRIMARY_LONG_HISTORY")

    def test_removing_the_true_team_forces_abstention(self) -> None:
        spine = dict(self.spine)
        spine.update(derive_spine_season_records(label_rows("TEAM:B", {2023: (8, 5, 0)})))
        verdict = resolve_organization(
            official_series=series_from(LONG_RECORD),
            spine_records=spine,
            contract=CONTRACT,
            excluded_team_ids=frozenset({"TEAM:A"}),
        )
        self.assertIsNone(verdict["canonical_team_id"])
        self.assertEqual(verdict["resolution_state"], "ABSTAINED")

    def test_season_shift_breaks_the_binding(self) -> None:
        verdict = resolve_organization(
            official_series=shift_series(series_from(LONG_RECORD)),
            spine_records=self.spine,
            contract=CONTRACT,
        )
        self.assertNotEqual(verdict["canonical_team_id"], "TEAM:A")

    def test_duplicate_history_is_ambiguous_and_abstains(self) -> None:
        spine = dict(self.spine)
        spine.update(derive_spine_season_records(label_rows("TEAM:TWIN", LONG_RECORD)))
        verdict = resolve_organization(
            official_series=series_from(LONG_RECORD), spine_records=spine, contract=CONTRACT
        )
        self.assertIsNone(verdict["canonical_team_id"])
        self.assertEqual(verdict["abstention_reason"], "AMBIGUOUS_RUNNER_UP_WITHIN_MARGIN")

    def test_short_history_requires_perfect_agreement(self) -> None:
        short = {2021: (5, 6, 0), 2022: (7, 4, 0), 2023: (6, 5, 0)}
        spine = derive_spine_season_records(label_rows("TEAM:S", short))
        exact = resolve_organization(
            official_series=series_from(short), spine_records=spine, contract=CONTRACT
        )
        self.assertEqual(exact["tier_id"], "SECONDARY_SHORT_HISTORY")
        self.assertEqual(exact["canonical_team_id"], "TEAM:S")

        blemished = dict(short)
        blemished[2022] = (8, 3, 0)
        imperfect = resolve_organization(
            official_series=series_from(blemished), spine_records=spine, contract=CONTRACT
        )
        self.assertIsNone(imperfect["canonical_team_id"])

    def test_too_few_seasons_abstains(self) -> None:
        tiny = {2023: (6, 5, 0)}
        spine = derive_spine_season_records(label_rows("TEAM:T", tiny))
        verdict = resolve_organization(
            official_series=series_from(tiny), spine_records=spine, contract=CONTRACT
        )
        self.assertIsNone(verdict["canonical_team_id"])
        self.assertEqual(verdict["abstention_reason"], "INSUFFICIENT_COMPARABLE_SEASONS")

    def test_no_candidate_abstains_rather_than_guessing(self) -> None:
        verdict = resolve_organization(
            official_series=series_from({1900: (5, 5, 0)}),
            spine_records=self.spine,
            contract=CONTRACT,
        )
        self.assertIsNone(verdict["canonical_team_id"])


class AcceptanceRuleTamperTests(unittest.TestCase):
    def test_lowering_the_margin_cannot_be_done_silently(self) -> None:
        scored = [
            {"canonical_team_id": "A", "compared_seasons": 20, "exact_matching_seasons": 20,
             "agreement_rate": 1.0},
            {"canonical_team_id": "B", "compared_seasons": 20, "exact_matching_seasons": 18,
             "agreement_rate": 0.9},
        ]
        self.assertIsNone(apply_acceptance_rules(scored, CONTRACT)["canonical_team_id"])

        tampered = json.loads(json.dumps(CONTRACT))
        tampered["acceptance_rules"]["tiers"][0]["minimum_exact_match_margin_over_runner_up"] = 1
        self.assertEqual(apply_acceptance_rules(scored, tampered)["canonical_team_id"], "A")

    def test_agreement_threshold_is_enforced(self) -> None:
        scored = [
            {"canonical_team_id": "A", "compared_seasons": 20, "exact_matching_seasons": 12,
             "agreement_rate": 0.6},
        ]
        verdict = apply_acceptance_rules(scored, CONTRACT)
        self.assertEqual(verdict["abstention_reason"], "AGREEMENT_RATE_BELOW_THRESHOLD")

    def test_empty_candidate_list_abstains(self) -> None:
        self.assertIsNone(apply_acceptance_rules([], CONTRACT)["canonical_team_id"])

    def test_score_candidates_ignores_seasons_absent_from_the_spine(self) -> None:
        spine = derive_spine_season_records(label_rows("TEAM:A", {2023: (8, 5, 0)}))
        scored = score_candidates({2023: (8, 5, 0), 1999: (1, 1, 0)}, spine)
        self.assertEqual(scored[0]["compared_seasons"], 1)


class ContractTests(unittest.TestCase):
    def test_predeclaration_is_recorded(self) -> None:
        self.assertTrue(CONTRACT["predeclaration"]["declared_before_reading_any_match_result"])

    def test_fuzzy_auto_accept_is_disabled(self) -> None:
        self.assertFalse(CONTRACT["acceptance_rules"]["fuzzy_auto_accept_enabled"])

    def test_sealed_seasons_are_declared_forbidden(self) -> None:
        self.assertEqual(CONTRACT["season_scope"]["forbidden_seasons"], [2024, 2025])

    def test_future_checkpoints_may_not_execute_early(self) -> None:
        preservation = CONTRACT["cohort_rebuild"]["checkpoint_preservation"]
        self.assertEqual(preservation["T_MINUS_24H"], "PRESERVE_AS_OPEN_AND_NEVER_EXECUTE_EARLY")
        self.assertEqual(preservation["T_MINUS_90M"], "PRESERVE_AS_OPEN_AND_NEVER_EXECUTE_EARLY")

    def test_non_claims_cover_the_prohibited_assertions(self) -> None:
        text = " ".join(CONTRACT["scientific_non_claims"]).lower()
        for token in ("battered aggie syndrome", "champion", "causal", "gap-002"):
            self.assertIn(token, text)


class DeterminismTests(unittest.TestCase):
    def test_payload_identity_is_order_sensitive_and_stable(self) -> None:
        rows = [{"b": 2, "a": 1}, {"a": 3}]
        self.assertEqual(payload_identity(rows), payload_identity([{"a": 1, "b": 2}, {"a": 3}]))
        self.assertNotEqual(payload_identity(rows), payload_identity(list(reversed(rows))))


class ArtifactTamperTests(unittest.TestCase):
    def _inputs(self) -> dict:
        spine = derive_spine_season_records(label_rows("TEAM:A", LONG_RECORD))
        acquisition = {
            "acquisitions": [
                {
                    "acquisition_state": "ACQUIRED",
                    "organization_id": 657,
                    "season_record_series": series_from(LONG_RECORD),
                }
            ],
            "official_organization_directory": {"Southern California": 657},
        }
        targets = {
            "organization_ids": [657],
            "organization_labels": {
                "Southern California": {
                    "gold_canonical_team_id": "TEAM:A",
                    "organization_id": 657,
                    "role": "GOLD_BENCHMARK",
                }
            },
        }
        cohort_rows = [
            {
                "checkpoints": [
                    {"checkpoint_id": "T_MINUS_24H", "deadline_utc": "2026-08-29T02:00:00Z",
                     "state": "OPEN"},
                    {"checkpoint_id": "T_MINUS_90M", "deadline_utc": "2026-08-30T00:30:00Z",
                     "state": "OPEN"},
                ],
                "cohort_state": "UNSUPPORTED_ENTITY",
                "ncaa_contest_id": "1",
                "participants": [
                    {"canonical_team_id": None, "source_display_name": "Southern California"}
                ],
                "unresolved_participant_names": ["Southern California"],
            }
        ]
        contract = json.loads(json.dumps(CONTRACT))
        return {
            "acquisition": acquisition,
            "acquisition_ledger_sha256": "b" * 64,
            "cohort_gate": {
                "contract_id": "PROSPECTIVE-2026-SHADOW-COHORT-001",
                "gate_identity": "a" * 64,
            },
            "cohort_predecessor_sha256": contract["cohort_rebuild"][
                "predecessor_payload_root_sha256"
            ],
            "cohort_rows": cohort_rows,
            "contract": contract,
            "execution_time_utc": "2026-08-29T18:00:00Z",
            "spine_gate": {"dataset_identity": "0" * 64},
            "spine_records": spine,
            "targets": targets,
        }

    def test_artifact_builds_and_reports_a_clean_benchmark(self) -> None:
        artifact = build_artifact(**self._inputs())
        gate = artifact["gate"]
        self.assertEqual(gate["benchmark_metrics"]["precision"], 1.0)
        self.assertEqual(gate["benchmark_metrics"]["conflict_rate"], 0.0)
        self.assertFalse(gate["identity_surfaces"]["fuzzy_auto_accept_enabled"])
        self.assertFalse(gate["protected_lane_opened"])

    def test_build_is_deterministic(self) -> None:
        first = build_artifact(**self._inputs())["gate"]["payload_root_sha256"]
        second = build_artifact(**self._inputs())["gate"]["payload_root_sha256"]
        self.assertEqual(first, second)

    def test_unsealing_a_forbidden_season_fails_closed(self) -> None:
        inputs = self._inputs()
        inputs["contract"]["season_scope"]["forbidden_seasons"] = [2025]
        with self.assertRaises(EntityBenchmarkViolation):
            build_artifact(**inputs)

    def test_raising_the_comparable_ceiling_into_sealed_years_fails_closed(self) -> None:
        inputs = self._inputs()
        inputs["contract"]["season_scope"]["maximum_comparable_season"] = 2025
        with self.assertRaises(EntityBenchmarkViolation):
            build_artifact(**inputs)

    def test_sealed_seasons_offered_by_the_source_are_discarded_and_reported(self) -> None:
        inputs = self._inputs()
        inputs["acquisition"]["acquisitions"][0]["season_record_series"].append(
            {
                "conference": "C", "division": "FBS", "losses": 4,
                "official_academic_year": "2024-25", "season": 2024,
                "team_season_id": None, "ties": 0, "wins": 9,
            }
        )
        gate = build_artifact(**inputs)["gate"]
        self.assertEqual(gate["forbidden_seasons_compared"], 0)
        self.assertEqual(
            gate["forbidden_seasons_offered_by_the_source_and_discarded"], [2024]
        )
        self.assertEqual(gate["benchmark_metrics"]["precision"], 1.0)

    def test_predecessor_identity_is_bound_into_the_successor(self) -> None:
        inputs = self._inputs()
        gate = build_artifact(**inputs)["gate"]
        self.assertEqual(
            gate["cohort_successor"]["predecessor_payload_sha256"],
            inputs["contract"]["cohort_rebuild"]["predecessor_payload_root_sha256"],
        )
        self.assertFalse(gate["cohort_successor"]["predecessor_is_rewritten"])

    def test_gate_identity_reproduces_from_the_gate_body(self) -> None:
        gate = build_artifact(**self._inputs())["gate"]
        body = dict(gate)
        committed = body.pop("gate_identity")
        self.assertEqual(committed, sha256_of(body))

    def test_successor_never_rewrites_the_predecessor(self) -> None:
        inputs = self._inputs()
        original = json.loads(json.dumps(inputs["cohort_rows"]))
        build_artifact(**inputs)
        self.assertEqual(inputs["cohort_rows"], original)

    def test_rebound_never_claims_new_frozen_coverage(self) -> None:
        gate = build_artifact(**self._inputs())["gate"]
        self.assertFalse(gate["coverage_rebound"]["frozen_or_scorable_coverage_changed"])
        self.assertEqual(gate["coverage_rebound"]["newly_supported_contests"], 1)

    def test_elapsed_and_open_checkpoints_are_distinguished_not_assumed(self) -> None:
        # At this instant T-24H (02:00Z) has elapsed but T-90M (next day) has not.
        gate = build_artifact(**self._inputs())["gate"]
        rebound = gate["coverage_rebound"]
        self.assertEqual(rebound["newly_supported_with_an_open_checkpoint"], 1)
        self.assertEqual(rebound["newly_supported_with_every_checkpoint_elapsed"], 0)

        late = self._inputs()
        late["execution_time_utc"] = "2026-09-30T00:00:00Z"
        late_rebound = build_artifact(**late)["gate"]["coverage_rebound"]
        self.assertEqual(late_rebound["newly_supported_with_an_open_checkpoint"], 0)
        self.assertEqual(late_rebound["newly_supported_with_every_checkpoint_elapsed"], 1)

    def test_open_checkpoint_state_names_the_deadline_it_must_not_execute(self) -> None:
        artifact = build_artifact(**self._inputs())
        successor = artifact["payloads"]["prospective_2026_shadow_cohort_successor.jsonl"][0]
        self.assertEqual(successor["cohort_state"], "ENTITY_SUPPORTED_WITH_A_CHECKPOINT_STILL_OPEN")
        self.assertIn("MUST_NOT_EXECUTE_IT_EARLY", successor["state_reason"])
        self.assertEqual(successor["open_checkpoints_at_successor_execution_time"], ["T_MINUS_90M"])

    def test_a_malformed_execution_time_fails_closed(self) -> None:
        inputs = self._inputs()
        inputs["execution_time_utc"] = "2026-08-29 18:00:00"
        with self.assertRaises(EntityBenchmarkViolation):
            build_artifact(**inputs)

    def test_future_checkpoints_keep_their_prohibition(self) -> None:
        artifact = build_artifact(**self._inputs())
        successor = artifact["payloads"]["prospective_2026_shadow_cohort_successor.jsonl"][0]
        for checkpoint in successor["checkpoints"]:
            self.assertEqual(
                checkpoint["preservation_policy"],
                "PRESERVE_AS_OPEN_AND_NEVER_EXECUTE_EARLY",
            )
            self.assertEqual(checkpoint["state"], "OPEN")

    def test_unacquired_organization_abstains_with_a_reason(self) -> None:
        inputs = self._inputs()
        inputs["acquisition"]["acquisitions"][0]["acquisition_state"] = "UNAVAILABLE"
        inputs["acquisition"]["acquisitions"][0]["reason"] = "direct_http:403"
        artifact = build_artifact(**inputs)
        row = artifact["payloads"]["national_entity_identity_resolutions.jsonl"][0]
        self.assertIsNone(row["canonical_team_id"])
        self.assertEqual(row["abstention_reason"], "OFFICIAL_EVIDENCE_UNAVAILABLE")
        self.assertEqual(row["official_evidence_unavailable_reason"], "direct_http:403")

    def test_conflicting_binding_is_counted_not_hidden(self) -> None:
        inputs = self._inputs()
        inputs["targets"]["organization_labels"]["Southern California"][
            "gold_canonical_team_id"
        ] = "TEAM:WRONG"
        gate = build_artifact(**inputs)["gate"]
        self.assertEqual(gate["benchmark_metrics"]["conflict_rate"], 1.0)
        self.assertEqual(gate["benchmark_metrics"]["precision"], 0.0)


if __name__ == "__main__":
    unittest.main()
