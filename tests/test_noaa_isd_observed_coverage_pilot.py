from __future__ import annotations

import unittest

from tools.acquire_noaa_isd_observed_coverage_pilot import station_file_id


class NoaaIsdObservedCoveragePilotTests(unittest.TestCase):
    def test_station_file_identity(self) -> None:
        self.assertEqual(station_file_id("722280-13876"), "72228013876")

    def test_station_file_identity_fails_closed(self) -> None:
        for invalid in ("72228013876", "72228-13876", "UNKNOWN-13876", "722280-1387"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                station_file_id(invalid)


if __name__ == "__main__":
    unittest.main()
