from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from aggie_analytics.features.gfs_multigame_selection import (
    candidate_runs,
    choose_attempt,
    parse_index_messages,
)


ROOT = Path(__file__).resolve().parents[1]


class NoaaGfsMultigameSelectionTests(unittest.TestCase):
    def test_candidate_runs_are_latest_first_and_valid_hour_bound(self) -> None:
        rows = candidate_runs(
            datetime(2024, 8, 30, 19, tzinfo=timezone.utc),
            datetime(2024, 8, 31, 19, tzinfo=timezone.utc),
            cycles_to_probe=5,
            maximum_forecast_hour=120,
        )
        self.assertEqual("2024-08-30T18:00:00Z", rows[0]["initialization_utc"])
        self.assertEqual(25, rows[0]["forecast_hour"])
        self.assertEqual("2024-08-30T12:00:00Z", rows[1]["initialization_utc"])
        self.assertEqual(31, rows[1]["forecast_hour"])
        self.assertTrue(all(rows[index]["forecast_hour"] < rows[index + 1]["forecast_hour"] for index in range(len(rows) - 1)))

    def test_choose_attempt_escalates_to_prior_cycle(self) -> None:
        selected = choose_attempt(
            [
                {"object_key": "newest", "disposition": "PUBLISHED_AFTER_CUTOFF"},
                {"object_key": "prior", "disposition": "AVAILABLE_BY_CUTOFF"},
            ]
        )
        self.assertEqual("prior", selected["object_key"])
        with self.assertRaises(RuntimeError):
            choose_attempt([{"object_key": "missing", "disposition": "OBJECT_UNAVAILABLE"}])

    def test_index_selects_exact_fields_and_shortest_precipitation_window(self) -> None:
        index = "\n".join(
            [
                "1:0:d=2023082312:TMP:2 m above ground:81 hour fcst:",
                "2:100:d=2023082312:DPT:2 m above ground:81 hour fcst:",
                "3:200:d=2023082312:APCP:surface:78-81 hour acc fcst:",
                "4:300:d=2023082312:APCP:surface:0-81 hour acc fcst:",
                "5:400:d=2023082312:TCDC:entire atmosphere:81 hour fcst:",
            ]
        )
        selected = parse_index_messages(
            index,
            [
                {"component": "temperature_2m", "descriptor": "TMP:2 m above ground"},
                {
                    "component": "precipitation_accumulation",
                    "descriptor": "APCP:surface",
                    "selection": "SHORTEST_NONZERO_ACCUMULATION_WINDOW_ENDING_AT_FORECAST_HOUR",
                },
            ],
            500,
            81,
        )
        self.assertEqual((0, 99), (selected[0]["range_start"], selected[0]["range_end"]))
        self.assertEqual(3, selected[1]["accumulation_hours"])
        self.assertEqual(78, selected[1]["accumulation_start_hour"])
        self.assertIn("78-81 hour acc", selected[1]["descriptor"])

    def test_contract_authority_is_bounded(self) -> None:
        contract = json.loads((ROOT / "configs/noaa_gfs_multigame_selection_contract.json").read_text())
        self.assertEqual(7, contract["population"]["expected_selection_rows"])
        self.assertEqual("1.43.2", contract["decoder"]["polars_package_version"])
        self.assertTrue(contract["authority"]["automatic_bounded_run_selection"])
        self.assertFalse(contract["authority"]["national_or_season_coverage"])
        self.assertFalse(contract["authority"]["canonical_venue_coordinate"])
        self.assertFalse(contract["authority"]["training_feature_admission"])
        self.assertFalse(contract["authority"]["protected_or_production"])


if __name__ == "__main__":
    unittest.main()
