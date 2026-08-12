from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from acquire_ncaa_official_gamebooks import stable_hash  # noqa: E402
from validate_ncaa_official_discovery import (  # noqa: E402
    discovery_manifest_core,
    validate_authority,
)


class NcaaOfficialDiscoveryValidationTests(unittest.TestCase):
    def test_discovery_identity_excludes_only_operational_fields(self) -> None:
        core = {
            "artifact_type": "NCAA_OFFICIAL_TEAM_GRAPH_DISCOVERY_MANIFEST",
            "season": 2023,
            "captures": [],
        }
        identity = stable_hash(core)
        manifest = {
            **core,
            "discovery_identity": identity,
            "issued_at_utc": "2026-08-12T11:20:00Z",
            "credentials_logged_or_persisted": False,
        }
        self.assertEqual(core, discovery_manifest_core(manifest))
        self.assertEqual(identity, stable_hash(discovery_manifest_core(manifest)))

    def test_candidate_only_authority_fails_closed(self) -> None:
        contract = json.loads(
            (ROOT / "configs" / "ncaa_official_gamebook_contract.json").read_text(
                encoding="utf-8"
            )
        )
        validate_authority(contract["authority"])
        for field in (
            "canonical_entity_mutation",
            "historical_pit_admission",
            "preliminary_training_admission",
            "protected_training_or_evaluation",
            "champion_or_production_promotion",
            "forecast_publication",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_authority({**contract["authority"], field: True})

    def test_rebuild_root_must_be_absent_before_validation(self) -> None:
        from validate_ncaa_official_discovery import validate_discovery

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "rebuild root already exists"):
                validate_discovery(
                    repo_root=ROOT,
                    data_root=root,
                    contract_path=ROOT
                    / "configs"
                    / "ncaa_official_gamebook_contract.json",
                    discovery_path=root / "missing.json",
                    rebuild_root=root,
                    env_file=None,
                )


if __name__ == "__main__":
    unittest.main()
