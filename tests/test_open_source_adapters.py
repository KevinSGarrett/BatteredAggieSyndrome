from __future__ import annotations

import json
import unittest

from aggie_analytics.data.adapters import AcquisitionRequest
from aggie_analytics.data.open_source import (
    StructuredClientTransport,
    deterministic_json_response,
    splink_settings,
)
from aggie_analytics.entities.candidates import FuzzyAliasCandidateGenerator
from aggie_analytics.entities.contracts import SourceEntityKey
from aggie_analytics.entities.resolution import AliasRecord


class OpenSourceAdapterTests(unittest.TestCase):
    def test_structured_transport_is_deterministic_and_credential_free(self) -> None:
        observed: dict[str, object] = {}

        def operation(**parameters):
            observed.update(parameters)
            return [{"team": "Texas A&M", "game_id": 2}, {"game_id": 1, "team": "Notre Dame"}]

        request = AcquisitionRequest(
            source_id="SPORTSDATAVERSE",
            dataset="schedule",
            source_uri="https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
            identity_components={"operation": "espn_cfb_scoreboard", "parameters": {"dates": "20240907"}},
            extension=".json",
        )
        response = StructuredClientTransport(operation, "espn_cfb_scoreboard")(request)
        self.assertEqual({"dates": "20240907"}, observed)
        self.assertEqual(2, response.row_count)
        self.assertEqual(("game_id", "team"), response.schema_fields)
        self.assertEqual(
            b'[{"game_id":2,"team":"Texas A&M"},{"game_id":1,"team":"Notre Dame"}]',
            response.body,
        )
        self.assertEqual(response.body, deterministic_json_response(json.loads(response.body)).body)

    def test_transport_rejects_operation_drift_and_secret_like_parameters(self) -> None:
        base = dict(
            source_id="CFBD",
            dataset="games",
            source_uri="https://api.collegefootballdata.com/games",
            extension=".json",
        )
        with self.assertRaisesRegex(ValueError, "operation mismatch"):
            StructuredClientTransport(lambda **_: [], "get_games")(
                AcquisitionRequest(**base, identity_components={"operation": "get_plays"})
            )
        with self.assertRaisesRegex(ValueError, "credential-like"):
            StructuredClientTransport(lambda **_: [], "get_games")(
                AcquisitionRequest(
                    **base,
                    identity_components={
                        "operation": "get_games",
                        "parameters": {"season": 2025, "api_token": "PLACEHOLDER"},
                    },
                )
            )
        with self.assertRaisesRegex(ValueError, "credential-like"):
            deterministic_json_response({"authorization_token": "PLACEHOLDER"})

    def test_fuzzy_candidates_are_ranked_but_never_promoted(self) -> None:
        scores = {
            ("texas a m", "texas a m"): 100.0,
            ("texas a m", "texas"): 78.0,
        }
        generator = FuzzyAliasCandidateGenerator(
            aliases=(
                AliasRecord("TEAM", "Texas", "team_texas"),
                AliasRecord("TEAM", "Texas A&M", "team_tamu"),
                AliasRecord("PLAYER", "Texas A&M", "player_not_applicable"),
            ),
            scorer=lambda left, right: scores.get((left, right), 0.0),
        )
        candidates = generator.generate(
            SourceEntityKey("CFBD", "TEAM", "245"),
            "Texas A & M",
            minimum_diagnostic_score=75,
            evidence_capture_ids=("capture-1",),
        )
        self.assertEqual(["team_tamu", "team_texas"], [item.candidate_canonical_id for item in candidates])
        self.assertTrue(all(item.mapping_method == "RAPIDFUZZ_DIAGNOSTIC_CANDIDATE" for item in candidates))
        self.assertFalse(any(hasattr(item, "selected_canonical_id") for item in candidates))

    def test_splink_settings_require_multi_field_bounded_review(self) -> None:
        settings = splink_settings(
            unique_id_column="source_player_id",
            match_columns=("normalized_name", "team_id", "class_year"),
            blocking_rules=("l.team_id = r.team_id",),
        )
        self.assertNotIn("threshold_match_probability", settings)
        self.assertTrue(settings["retain_matching_columns"])
        with self.assertRaisesRegex(ValueError, "at least two"):
            splink_settings(
                unique_id_column="id",
                match_columns=("name",),
                blocking_rules=("l.team = r.team",),
            )

    def test_fuzzy_candidate_scorer_cannot_emit_invalid_probability_like_evidence(self) -> None:
        generator = FuzzyAliasCandidateGenerator(
            (AliasRecord("TEAM", "Texas A&M", "team_tamu"),),
            scorer=lambda _left, _right: float("nan"),
        )
        with self.assertRaisesRegex(ValueError, "finite value"):
            generator.generate(SourceEntityKey("CFBD", "TEAM", "245"), "Texas A&M")


if __name__ == "__main__":
    unittest.main()
