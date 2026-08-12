from __future__ import annotations

from datetime import datetime, timezone
import unittest

from aggie_analytics.features.observed_weather_shadow import (
    decode_observation,
    select_temporal_candidates,
    station_file_id,
)


class NoaaIsdGameObservationShadowTests(unittest.TestCase):
    def test_decode_common_fields_and_sentinels(self) -> None:
        row = {
            "DATE": "2024-09-01T00:00:00",
            "TMP": "+0057,1",
            "DEW": "+9999,9",
            "WND": "260,1,N,0080,1",
            "VIS": "016000,1,9,9",
            "SLP": "09946,1",
            "AA1": "06,0001,3,1",
            "REPORT_TYPE": "FM-15",
            "SOURCE": "7",
        }
        decoded = decode_observation(row, 2)
        self.assertEqual(decoded["temperature_c"], 5.7)
        self.assertIsNone(decoded["dew_point_c"])
        self.assertEqual(decoded["wind_direction_degrees"], 260)
        self.assertEqual(decoded["wind_speed_mps"], 8.0)
        self.assertEqual(decoded["visibility_m"], 16000.0)
        self.assertEqual(decoded["sea_level_pressure_hpa"], 994.6)
        self.assertIn("AA1", decoded["precipitation_raw_json"])

    def test_temporal_selection_preserves_both_sides_and_earlier_tie(self) -> None:
        observations = [
            {"observed_at_utc": "2024-09-01T17:00:00Z"},
            {"observed_at_utc": "2024-09-01T19:00:00Z"},
        ]
        kickoff = datetime(2024, 9, 1, 18, 0, tzinfo=timezone.utc)
        selected = select_temporal_candidates(observations, kickoff)
        self.assertEqual(selected["before"]["observed_at_utc"], "2024-09-01T17:00:00Z")
        self.assertEqual(selected["after"]["observed_at_utc"], "2024-09-01T19:00:00Z")
        self.assertEqual(selected["nearest"]["observed_at_utc"], "2024-09-01T17:00:00Z")

    def test_station_file_id_fails_closed(self) -> None:
        self.assertEqual(station_file_id("722280-13876"), "72228013876")
        with self.assertRaises(ValueError):
            station_file_id("72228013876")


if __name__ == "__main__":
    unittest.main()
