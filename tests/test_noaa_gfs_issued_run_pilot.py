from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.features.gfs_issued_run import parse_index

ROOT = Path(__file__).resolve().parents[1]


class NoaaGfsIssuedRunPilotTests(unittest.TestCase):
    def test_index_range_and_authority(self) -> None:
        rows = parse_index(
            "1:0:d=2024083012:TMP:2 m above ground:31 hour fcst:\n2:100:d=2024083012:DPT:2 m above ground:31 hour fcst:\n3:180:d=2024083012:RH:2 m above ground:31 hour fcst:\n",
            [{"component": "temperature_2m", "match": ":TMP:2 m above ground:31 hour fcst:"}],
            250,
        )
        self.assertEqual((0, 99, 100), (rows[0]["range_start"], rows[0]["range_end"], rows[0]["range_bytes"]))
        contract = json.loads((ROOT / "configs/noaa_gfs_issued_run_pilot_contract.json").read_text())
        self.assertTrue(contract["authority"]["exact_run_availability_proof"])
        self.assertFalse(contract["authority"]["automatic_national_run_selection"])
        self.assertFalse(contract["authority"]["training_feature_admission"])
        self.assertFalse(contract["authority"]["protected_or_production"])


if __name__ == "__main__": unittest.main()
