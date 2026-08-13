from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from aggie_analytics.data.adapters import FetchResponse  # noqa: E402
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402
from acquire_ncaa_official_gamebooks import discover_season, stable_hash  # noqa: E402
from validate_ncaa_official_discovery import (  # noqa: E402
    discovery_manifest_core,
    validate_authority,
    validate_discovery,
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

    def test_legacy_schedule_manifest_replays_candidate_only_evidence(self) -> None:
        contract_path = ROOT / "configs" / "ncaa_official_gamebook_contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        seed_team_season_id = str(
            contract["discovery"]["seed_team_season_ids"]["2010"]
        )
        filler = "<div>NCAA official team statistics</div>" * 40
        body = (
            "<html><body>NCAA<table>"
            f"<tr><td>09/04/2010</td><td><a href='/teams/{seed_team_season_id}'>"
            "@ San Jose St.</a></td>"
            "<td>W 48 - 3</td></tr>"
            f"</table>{filler}</body></html>"
        ).encode("utf-8")

        class FakeBrowser:
            def fetch(self, uri):
                return FetchResponse(body=body, status_code=200)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_root = root / "data"
            data_root.mkdir()
            result = discover_season(
                season=2010,
                contract=contract,
                store=RawSnapshotStore(data_root),
                browser=FakeBrowser(),
                retrieved_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
                maximum_teams=10,
            )
            report, _ = validate_discovery(
                repo_root=ROOT,
                data_root=data_root,
                contract_path=contract_path,
                discovery_path=Path(result["manifest_path"]),
                rebuild_root=root / "rebuild",
                env_file=None,
            )
            self.assertEqual("PASS", report["result"])
            self.assertEqual(1, report["legacy_schedule_record_count"])

            promoted = json.loads(
                Path(result["manifest_path"]).read_text(encoding="utf-8")
            )
            promoted["captures"][0]["legacy_schedule_records"][0][
                "contest_id"
            ] = "fabricated-contest"
            promoted_core = discovery_manifest_core(promoted)
            promoted_identity = stable_hash(promoted_core)
            promoted["discovery_identity"] = promoted_identity
            promoted_path = (
                data_root
                / "manifests"
                / "mutation_control"
                / "sha256"
                / promoted_identity
                / "ncaa_team_graph_discovery_manifest.json"
            )
            promoted_path.parent.mkdir(parents=True)
            promoted_path.write_text(
                json.dumps(promoted, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaisesRegex(AssertionError, "profile_legacy_schedule"):
                validate_discovery(
                    repo_root=ROOT,
                    data_root=data_root,
                    contract_path=contract_path,
                    discovery_path=promoted_path,
                    rebuild_root=root / "rebuild-promoted",
                    env_file=None,
                )


if __name__ == "__main__":
    unittest.main()
