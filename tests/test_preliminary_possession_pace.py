from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.features.possession_pace import (
    _verify_source_manifests,
    observed_regulation_drive_span_seconds,
    regulation_elapsed_seconds,
)


ROOT = Path(__file__).resolve().parents[1]


class PreliminaryPossessionPaceContractTests(unittest.TestCase):
    def test_regulation_elapsed_seconds(self) -> None:
        self.assertEqual(0, regulation_elapsed_seconds(1, 15, 0))
        self.assertEqual(900, regulation_elapsed_seconds(1, 0, 0))
        self.assertEqual(900, regulation_elapsed_seconds(2, 15, 0))
        self.assertEqual(3600, regulation_elapsed_seconds(4, 0, 0))
        self.assertIsNone(regulation_elapsed_seconds(5, 0, 0))
        self.assertIsNone(regulation_elapsed_seconds(1, 16, 0))
        self.assertIsNone(regulation_elapsed_seconds(1, 15, 1))

    def test_span_normalizes_source_endpoint_order(self) -> None:
        self.assertEqual((100, False), observed_regulation_drive_span_seconds(1, 12, 0, 1, 10, 20))
        self.assertEqual((100, True), observed_regulation_drive_span_seconds(1, 10, 20, 1, 12, 0))
        self.assertEqual((None, None), observed_regulation_drive_span_seconds(5, 0, 0, 5, 0, 0))

    def test_contract_preserves_unsupported_metrics_and_authority(self) -> None:
        contract = json.loads((ROOT / "configs" / "preliminary_possession_pace_contract.json").read_text(encoding="utf-8"))
        unsupported = contract["feature_contract"]["unsupported_fields"]
        self.assertIn("true_possession_time", unsupported)
        self.assertIn("seconds_per_snap", unsupported)
        self.assertFalse(contract["authority"]["protected_training_admission"])
        self.assertFalse(contract["authority"]["champion_or_production_promotion"])
        self.assertEqual("PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE", contract["classification"])

    def test_contract_does_not_assume_source_order_is_chronological(self) -> None:
        contract = json.loads((ROOT / "configs" / "preliminary_possession_pace_contract.json").read_text(encoding="utf-8"))
        self.assertFalse(contract["eligibility"]["source_order_assumed_chronological"])
        self.assertEqual(0, contract["acceptance"]["negative_drive_span_rows_allowed"])

    def test_source_manifest_hash_verification_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            play_bytes = b'{"source":"play"}\n'
            target_bytes = b'{"source":"target"}\n'
            play_identity = "a" * 64
            target_identity = "b" * 64
            play_root = root / "manifests" / "historical_known_at" / "sha256" / play_identity
            target_root = root / "manifests" / "historical_known_at" / "sha256" / target_identity
            play_root.mkdir(parents=True)
            target_root.mkdir(parents=True)
            (play_root / "source.json").write_bytes(play_bytes)
            (target_root / "target.json").write_bytes(target_bytes)
            contract = {
                "source_contract": {
                    "source_layers": [{
                        "play_dataset_identity": play_identity,
                        "play_manifest_sha256": hashlib.sha256(play_bytes).hexdigest(),
                        "drive_dataset_identity": play_identity,
                        "drive_manifest_sha256": hashlib.sha256(play_bytes).hexdigest(),
                    }],
                    "target_replay_identity": target_identity,
                    "target_replay_manifest_sha256": hashlib.sha256(target_bytes).hexdigest(),
                }
            }
            self.assertEqual(2, len(_verify_source_manifests(root, contract)))
            contract["source_contract"]["target_replay_manifest_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                _verify_source_manifests(root, contract)


if __name__ == "__main__":
    unittest.main()
