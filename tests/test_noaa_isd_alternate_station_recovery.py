from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NoaaIsdAlternateStationRecoveryTests(unittest.TestCase):
    def test_contract_forbids_automatic_selection_and_feature_admission(self) -> None:
        contract = json.loads((ROOT / "configs/noaa_isd_alternate_station_recovery_contract.json").read_text(encoding="utf-8"))
        self.assertFalse(contract["selection"]["automatic_alternate_station_selection"])
        self.assertFalse(contract["selection"]["automatic_station_acceptance"])
        self.assertIsNone(contract["selection"]["maximum_time_delta_minutes"])
        self.assertFalse(contract["authority"]["canonical_station_acceptance"])
        self.assertFalse(contract["authority"]["game_feature_admission"])
        self.assertFalse(contract["population"]["recovery_rule_is_feature_acceptance_threshold"])


if __name__ == "__main__":
    unittest.main()
