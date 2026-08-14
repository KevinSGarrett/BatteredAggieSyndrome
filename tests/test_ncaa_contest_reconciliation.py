from __future__ import annotations

import unittest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

try:
    import polars as pl
except ImportError:  # pragma: no cover - exercised by the minimal hosted test environment
    pl = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation import (  # noqa: E402
    normalize_team_name,
    parse_legacy_team_page,
    parse_team_page,
    reconcile,
    sha256_file,
)
from tools.validate_ncaa_contest_reconciliation import main as validate_reconciliation  # noqa: E402


class NcaaContestReconciliationTests(unittest.TestCase):
    def test_normalization_is_exact_but_punctuation_stable(self) -> None:
        self.assertEqual(normalize_team_name("Texas A&M"), "texas a and m")
        self.assertEqual(normalize_team_name("San Jos\u00e9 St."), "san jose state")
        self.assertEqual(normalize_team_name("Birmingham-So."), "birmingham southern")

    def test_team_page_parser_preserves_oriented_score_and_ids(self) -> None:
        payload = """
        <div class="card-header"><img class="logo_image" alt="Texas A&M" src="https://x/All_Logos/sm//697.gif"> Texas A&M Aggies</div>
        <tr class="underline_rows">
          <td>09/02/2023</td>
          <td>@<a href="/teams/557111"><img alt="New Mexico" src="x"></a></td>
          <td><a href="/contests/1234567/box_score">W 52-10</a></td>
        </tr>
        """
        page, rows = parse_team_page(payload, team_season_id="557999", raw_sha256="a" * 64)
        self.assertIsNotNone(page)
        self.assertEqual(page["source_team_org_id"], "697")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["contest_id"], "1234567")
        self.assertEqual(rows[0]["source_team_points"], 52)
        self.assertEqual(rows[0]["opponent_points"], 10)
        self.assertTrue(rows[0]["source_team_is_away"])

    def test_team_page_parser_accepts_classless_text_link_schedule_rows(self) -> None:
        payload = """
        <div class="card-header"><img alt="Benedict" src="https://x/All_Logos/sm//55.gif"></div>
        <table><tbody>
        <tr>
          <td class="smtext">09/07/2013</td>
          <td class="smtext"><a href="/teams/62414">@ Central St. (OH)</a></td>
          <td class="smtext"><a target="TEAM_WIN" class="skipMask" href="/contests/689047/box_score">W 42 - 9</a></td>
        </tr>
        <tr>
          <td class="smtext">09/14/2013</td>
          <td class="smtext"><a href="/teams/62346">Virginia St.<br>@ East Rutherford, NJ</a></td>
          <td class="smtext"><a href="/contests/689593/box_score">W 30 - 14</a></td>
        </tr>
        </tbody></table>
        """
        page, rows = parse_team_page(
            payload, team_season_id="62275", raw_sha256="e" * 64
        )
        self.assertIsNotNone(page)
        self.assertEqual(page["source_team_org_id"], "55")
        self.assertEqual(page["scored_schedule_rows"], 2)
        self.assertEqual([row["contest_id"] for row in rows], ["689047", "689593"])
        self.assertEqual(rows[0]["opponent_team_season_id"], "62414")
        self.assertEqual(rows[0]["opponent_team_name"], "Central St. (OH)")
        self.assertTrue(rows[0]["source_team_is_away"])
        self.assertEqual(rows[1]["opponent_team_name"], "Virginia St. @ East Rutherford, NJ")
        self.assertFalse(rows[1]["source_team_is_away"])

    def test_unrecognized_owner_fails_closed(self) -> None:
        page, rows = parse_team_page("<html>challenge</html>", team_season_id="1", raw_sha256="b" * 64)
        self.assertIsNone(page)
        self.assertEqual(rows, [])

    def test_legacy_parser_preserves_team_link_and_does_not_invent_contest_id(self) -> None:
        payload = """
        <div class="card-header"><img class="logo_image" alt="TCU" src="https://x/All_Logos/sm//698.gif"> TCU Horned Frogs</div>
        <tr><td class="smtext">09/02/2011</td><td><a href="/teams/137690">@ Baylor</a></td><td>48 - 50</td></tr>
        """
        page, rows = parse_legacy_team_page(payload, team_season_id="137844", raw_sha256="c" * 64)
        self.assertIsNotNone(page)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["contest_id"])
        self.assertEqual(rows[0]["opponent_team_season_id"], "137690")
        self.assertEqual(rows[0]["source_team_points"], 48)
        self.assertEqual(rows[0]["opponent_points"], 50)
        self.assertTrue(rows[0]["source_team_is_away"])
        self.assertFalse(rows[0]["source_result_was_explicit"])
        self.assertEqual(rows[0]["source_result"], "L")

    def test_legacy_parser_excludes_modern_contest_rows(self) -> None:
        payload = """
        <div class="card-header"><img class="logo_image" alt="Texas A&amp;M" src="https://x/All_Logos/sm//697.gif"></div>
        <tr class="underline_rows"><td>09/02/2023</td><td><a href="/teams/557111">@ New Mexico</a></td>
        <td><a href="/contests/1234567/box_score">W 52 - 10</a></td></tr>
        """
        page, rows = parse_legacy_team_page(payload, team_season_id="557999", raw_sha256="d" * 64)
        self.assertIsNotNone(page)
        self.assertEqual(rows, [])

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_two_sided_legacy_rows_reconcile_without_contest_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_root = Path(temporary)
            raw_root = data_root / "raw"
            raw_root.mkdir()
            tcu = raw_root / "tcu.html"
            baylor = raw_root / "baylor.html"
            tcu.write_text(
                '<div class="card-header"><img alt="TCU" src="x/All_Logos/sm//698.gif"></div>'
                '<tr><td>09/02/2011</td><td><a href="/teams/137690">@ Baylor</a></td><td>48 - 50</td></tr>',
                encoding="utf-8",
            )
            baylor.write_text(
                '<div class="card-header"><img alt="Baylor" src="x/All_Logos/sm//239.gif"></div>'
                '<tr><td>09/02/2011</td><td><a href="/teams/137844">TCU</a></td><td>50 - 48</td></tr>',
                encoding="utf-8",
            )
            discovery = {
                "season": 2011,
                "state": "COMPLETE_GRAPH_EXHAUSTED",
                "discovered_contest_ids": [],
                "captures": [
                    {"team_season_id": "137844", "raw_relative_path": "raw/tcu.html", "raw_sha256": sha256_file(tcu)},
                    {"team_season_id": "137690", "raw_relative_path": "raw/baylor.html", "raw_sha256": sha256_file(baylor)},
                ],
            }
            discovery_path = data_root / "discovery.json"
            discovery_path.write_text(json.dumps(discovery), encoding="utf-8")
            registry_path = data_root / "registry.csv"
            pl.DataFrame([
                {"record_type": "ALIAS", "entity_type": "team", "resolution_state": "AUTO_ACCEPTED_VERIFIED", "canonical_id": "team_tcu", "alias": "TCU"},
                {"record_type": "ALIAS", "entity_type": "team", "resolution_state": "AUTO_ACCEPTED_VERIFIED", "canonical_id": "team_baylor", "alias": "Baylor"},
            ]).write_csv(registry_path)
            outcomes_path = data_root / "outcomes.parquet"
            pl.DataFrame([{
                "target_game_id": "game_2011_tcu_baylor",
                "season": 2011,
                "season_type": "regular",
                "week": 1,
                "start_utc": "2011-09-02T23:00:00Z",
                "home_team_id": "team_baylor",
                "away_team_id": "team_tcu",
                "home_points": 50,
                "away_points": 48,
            }]).write_parquet(outcomes_path)
            contract = {
                "schema_version": "2.0.0",
                "contract_id": "test-legacy-reconciliation",
                "decision_unit": "POST-SUBTASK-197",
                "jira_key": "BAT-554",
                "classification": "CANDIDATE_ONLY_DETERMINISTIC_TWO_SIDED_CONTEXT_RECONCILIATION",
                "source_contract": {
                    "season": 2011,
                    "discovery_manifest": "discovery.json",
                    "discovery_manifest_sha256": sha256_file(discovery_path),
                    "canonical_registry": "registry.csv",
                    "canonical_registry_sha256": sha256_file(registry_path),
                    "outcome_targets": "outcomes.parquet",
                    "outcome_targets_sha256": sha256_file(outcomes_path),
                },
                "admission": {"maximum_source_date_to_utc_date_delta_days": 1},
                "authority": {
                    "canonical_registry_write": False,
                    "historical_pit_eligible": False,
                    "training_eligible": False,
                    "protected_evaluation_eligible": False,
                    "production_eligible": False,
                },
            }
            contract_path = data_root / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            result = reconcile(
                input_data_root=data_root,
                output_data_root=data_root,
                repo_root=ROOT,
                contract_path=contract_path,
                issued_at_utc="2026-08-14T00:00:00Z",
            )

            self.assertEqual(result["population"]["reconciled_contests"], 0)
            self.assertEqual(result["population"]["reconciled_legacy_games"], 1)
            self.assertEqual(result["population"]["unresolved_legacy_observations"], 0)
            artifact_root = Path(result["feature_root"])
            modern = pl.read_parquet(artifact_root / "contest_mappings.parquet")
            unresolved = pl.read_parquet(artifact_root / "unresolved_contests.parquet")
            observations = pl.read_parquet(artifact_root / "source_schedule_observations.parquet")
            self.assertEqual(modern.height, 0)
            self.assertIn("ncaa_contest_id", modern.columns)
            self.assertEqual(modern.schema["ncaa_contest_id"], pl.String)
            self.assertEqual(unresolved.height, 0)
            self.assertIn("reason", unresolved.columns)
            self.assertEqual(observations.height, 0)
            self.assertIn("contest_id", observations.columns)

            mapping = pl.read_parquet(artifact_root / "legacy_schedule_mappings.parquet").to_dicts()[0]
            self.assertIsNone(mapping["ncaa_contest_id"])
            self.assertFalse(mapping["contest_id_fabricated"])
            self.assertEqual(mapping["canonical_game_id"], "game_2011_tcu_baylor")

            manifest_path = Path(result["manifest_path"])
            manifest_before = manifest_path.read_bytes()
            payload_before = {
                path.name: path.read_bytes()
                for path in artifact_root.glob("*.parquet")
            }
            replay = reconcile(
                input_data_root=data_root,
                output_data_root=data_root,
                repo_root=ROOT,
                contract_path=contract_path,
                issued_at_utc="2026-08-14T00:00:00Z",
            )
            self.assertEqual(result["dataset_identity"], replay["dataset_identity"])
            self.assertEqual(manifest_before, manifest_path.read_bytes())
            self.assertEqual(
                payload_before,
                {path.name: path.read_bytes() for path in artifact_root.glob("*.parquet")},
            )
            with self.assertRaisesRegex(
                ValueError, "immutable reconciliation manifest collision"
            ):
                reconcile(
                    input_data_root=data_root,
                    output_data_root=data_root,
                    repo_root=ROOT,
                    contract_path=contract_path,
                    issued_at_utc="2026-08-14T00:00:01Z",
                )
            self.assertEqual(manifest_before, manifest_path.read_bytes())
            self.assertEqual(
                payload_before,
                {path.name: path.read_bytes() for path in artifact_root.glob("*.parquet")},
            )

            with patch(
                "sys.argv",
                [
                    "validate_ncaa_contest_reconciliation.py",
                    "--data-root", str(data_root),
                    "--rebuild-root", str(data_root / "rebuild"),
                    "--repo-root", str(ROOT),
                    "--contract", str(contract_path),
                    "--dataset-identity", result["dataset_identity"],
                ],
            ):
                self.assertEqual(validate_reconciliation(), 0)


if __name__ == "__main__":
    unittest.main()
