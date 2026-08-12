from __future__ import annotations

from datetime import date
import unittest

from aggie_analytics.features.weather_station_matching import (
    haversine_km,
    parse_isd_station_catalog,
    rank_station_candidates,
    station_period_covers_season,
)


class NoaaIsdStationMatchingTests(unittest.TestCase):
    def test_haversine_identity_and_known_distance(self) -> None:
        self.assertEqual(haversine_km(30.0, -97.0, 30.0, -97.0), 0.0)
        self.assertAlmostEqual(haversine_km(0.0, 0.0, 0.0, 1.0), 111.19508, places=4)

    def test_station_period_overlap_is_season_specific(self) -> None:
        begin, end = date(2014, 6, 1), date(2020, 2, 1)
        self.assertTrue(station_period_covers_season(begin, end, 2014))
        self.assertTrue(station_period_covers_season(begin, end, 2020))
        self.assertFalse(station_period_covers_season(begin, end, 2013))
        self.assertFalse(station_period_covers_season(begin, end, 2021))

    def test_parser_rejects_invalid_coordinates_and_dates(self) -> None:
        payload = (
            "USAF,WBAN,STATION NAME,CTRY,STATE,ICAO,LAT,LON,ELEV(M),BEGIN,END\n"
            "1,2,Good,US,TX,KAAA,30,-97,100,20100101,20251231\n"
            "3,4,Bad coordinate,US,TX,KBBB,missing,-97,100,20100101,20251231\n"
            "5,6,Bad date,US,TX,KCCC,30,-97,100,20109999,20251231\n"
        ).encode()
        rows = parse_isd_station_catalog(payload)
        self.assertEqual([row["station_id"] for row in rows], ["1-2"])

    def test_ranking_is_distance_then_station_identity_and_period_gated(self) -> None:
        stations = [
            {"station_id": "B-1", "latitude": 0.0, "longitude": 1.0, "begin": date(2010, 1, 1), "end": date(2030, 1, 1)},
            {"station_id": "A-1", "latitude": 0.0, "longitude": -1.0, "begin": date(2010, 1, 1), "end": date(2030, 1, 1)},
            {"station_id": "C-1", "latitude": 0.0, "longitude": 0.1, "begin": date(1990, 1, 1), "end": date(2000, 1, 1)},
        ]
        for row in stations:
            row.update({"station_name": "", "country": "", "state": "", "icao": "", "elevation_m": ""})
        ranked = rank_station_candidates(0.0, 0.0, 2020, stations, 2)
        self.assertEqual([row["station_id"] for row in ranked], ["A-1", "B-1"])


if __name__ == "__main__":
    unittest.main()
