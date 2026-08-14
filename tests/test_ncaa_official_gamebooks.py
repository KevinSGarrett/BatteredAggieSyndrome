from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from acquire_ncaa_official_gamebooks import (  # noqa: E402
    DirectHTTPTransport,
    ScrapflyTransport,
    ScraperAPITransport,
    ValidatingTransport,
    acquire_one,
    build_gate,
    build_discovery_routes,
    build_routes,
    discover_season,
    inspect_ncaa_html,
    inspect_ncaa_team_page,
    load_optional_dotenv_value,
    load_reconciled_contests,
    main,
    normalize_ncaa_capture,
    request_for,
    validate_official_uri,
)
from aggie_analytics.data.adapters import AcquisitionFailure, FetchResponse  # noqa: E402
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402


class NcaaOfficialGamebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_path = ROOT / "configs" / "ncaa_official_gamebook_contract.json"
        cls.contract = json.loads(cls.contract_path.read_text(encoding="utf-8"))

    def fixture(self, endpoint_id: str, marker: str) -> bytes:
        rows = "".join(f"<tr><td>{index}</td><td>value</td></tr>" for index in range(80))
        return (
            "<!doctype html><html><head><title>NCAA Statistics</title></head>"
            f"<body><h1>{marker}</h1><div>Official NCAA contest evidence</div>"
            f"<table><thead><tr><th>Team</th><th>{endpoint_id}</th></tr></thead><tbody>{rows}</tbody></table>"
            "</body></html>"
        ).encode("utf-8")

    def test_contract_is_candidate_only_and_partial_domains_do_not_globally_block(self) -> None:
        authority = self.contract["authority"]
        self.assertTrue(authority["immutable_private_raw_archive"])
        self.assertTrue(authority["candidate_normalization_and_reconciliation"])
        for key in (
            "canonical_entity_mutation",
            "historical_pit_admission",
            "preliminary_training_admission",
            "protected_training_or_evaluation",
            "champion_or_production_promotion",
            "forecast_publication",
        ):
            self.assertFalse(authority[key])
        self.assertTrue(self.contract["scale_out_gate"]["partial_domain_does_not_block_unrelated_valid_domains"])
        self.assertFalse(self.contract["scale_out_gate"]["automatic_national_scale_out_enabled"])

    def test_every_endpoint_fixture_passes_with_measured_schema(self) -> None:
        markers = {
            "box_score": "Box Score and Team Statistics",
            "play_by_play": "Play-by-Play",
            "drives": "Drives",
            "team_stats": "Team Statistics",
            "individual_stats": "Individual Statistics and Passing",
            "officials": "Officials and Referee",
        }
        for endpoint_id, marker in markers.items():
            with self.subTest(endpoint_id=endpoint_id):
                result = inspect_ncaa_html(
                    self.fixture(endpoint_id, marker),
                    contest_id="5362283",
                    endpoint_id=endpoint_id,
                    contract=self.contract,
                )
                self.assertEqual("PASS", result["content_validation"])
                self.assertGreater(result["row_count"], 0)
                self.assertGreater(result["table_count"], 0)
                self.assertIn(endpoint_id, result["schema_fields"])

    def test_interstitial_thin_and_schema_drift_payloads_fail_closed(self) -> None:
        with self.assertRaisesRegex(AcquisitionFailure, "anti-bot") as interstitial:
            inspect_ncaa_html(
                b"<html><body>NCAA bm-verify _abck</body></html>",
                contest_id="5362283",
                endpoint_id="box_score",
                contract=self.contract,
            )
        self.assertEqual("ANTI_BOT_INTERSTITIAL", interstitial.exception.condition)
        with self.assertRaises(AcquisitionFailure) as thin:
            inspect_ncaa_html(
                b"<html><body>NCAA Box Score</body></html>",
                contest_id="5362283",
                endpoint_id="box_score",
                contract=self.contract,
            )
        self.assertEqual("CONTENT_TOO_SMALL", thin.exception.condition)
        with self.assertRaises(AcquisitionFailure) as drift:
            inspect_ncaa_html(
                self.fixture("box_score", "Unrecognized new layout"),
                contest_id="5362283",
                endpoint_id="box_score",
                contract=self.contract,
            )
        self.assertEqual("SCHEMA_INCOMPATIBLE", drift.exception.condition)

    def test_official_uri_allowlist_rejects_queries_credentials_and_other_hosts(self) -> None:
        validate_official_uri("https://stats.ncaa.org/contests/5362283/box_score")
        validate_official_uri("https://stats.ncaa.org/teams/589027")
        for value in (
            "http://stats.ncaa.org/contests/5362283/box_score",
            "https://example.com/contests/5362283/box_score",
            "https://user:password@stats.ncaa.org/contests/5362283/box_score",
            "https://stats.ncaa.org/contests/5362283/box_score?token=secret",
            "https://stats.ncaa.org/team/1",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_official_uri(value)

    def test_team_page_discovery_extracts_team_contest_and_season_identities(self) -> None:
        filler = "<div>NCAA official team statistics</div>" * 40
        body = (
            "<html><body>NCAA"
            "<table><tr><td><a href='/teams/589027'>A</a><a href='/teams/589036'>B</a>"
            "<a href='/contests/5362283/box_score'>Game</a></td></tr></table>"
            "<select><option value='589027'>2024-25</option><option value='557196'>2023-24</option></select>"
            f"{filler}</body></html>"
        ).encode("utf-8")
        result = inspect_ncaa_team_page(body, contract=self.contract)
        self.assertEqual(["5362283"], result["contest_ids"])
        self.assertEqual(["589027", "589036"], result["team_season_ids"])
        self.assertEqual("589027", result["season_options"]["2024-25"])
        self.assertEqual("MODERN_CONTEST_ROW", result["link_schema"])

    def test_legacy_team_page_discovery_traverses_schedule_results_without_inventing_contests(self) -> None:
        filler = "<div>NCAA official team statistics</div>" * 40
        body = (
            "<html><body>NCAA<table>"
            "<tr><td>09/04/2010</td><td><a href='/teams/136978'>Arkansas St.</a></td>"
            "<td>W 52 - 26</td></tr>"
            "<tr><td>09/17/2011</td><td><a href='/teams/137712'>Clemson</a></td>"
            "<td>24 - 38</td></tr>"
            "<tr><td>Navigation</td><td><a href='/teams/999999'>Not a schedule opponent</a></td></tr>"
            "</table><select><option value='136982'>2010-11</option></select>"
            f"{filler}</body></html>"
        ).encode("utf-8")
        result = inspect_ncaa_team_page(body, contract=self.contract)
        self.assertEqual([], result["contest_ids"])
        self.assertEqual(["136978", "137712"], result["team_season_ids"])
        self.assertEqual("LEGACY_SCHEDULE_RESULT_ROW", result["link_schema"])
        self.assertEqual(2, result["legacy_schedule_record_count"])
        self.assertEqual(
            {
                "game_date": "2010-09-04",
                "opponent_team_season_id": "136978",
                "opponent_display_name": "Arkansas St.",
                "site_hint": "HOME_OR_NEUTRAL_UNKNOWN",
                "explicit_result_code": "W",
                "score_for": 52,
                "score_against": 26,
                "contest_id": None,
                "canonical_game_id": None,
                "reconciliation_state": "SOURCE_LINKED_CANDIDATE_ONLY",
                "source_row_sha256": result["legacy_schedule_records"][0]["source_row_sha256"],
            },
            result["legacy_schedule_records"][0],
        )
        self.assertEqual("UNKNOWN", result["legacy_schedule_records"][1]["explicit_result_code"])
        self.assertIsNone(result["legacy_schedule_records"][1]["contest_id"])
        self.assertIsNone(result["legacy_schedule_records"][1]["canonical_game_id"])

    def test_legacy_schedule_records_preserve_away_hint_without_promoting_home_or_neutral(self) -> None:
        filler = "<div>NCAA official team statistics</div>" * 40
        body = (
            "<html><body>NCAA<table>"
            "<tr><td>09/04/2010</td><td><a href='/teams/137345'>@ San Jose St.</a></td>"
            "<td>W 48 - 3</td></tr>"
            "<tr><td>bad date</td><td><a href='/teams/1'>Ignored</a></td><td>W 1 - 0</td></tr>"
            "</table>"
            f"{filler}</body></html>"
        ).encode("utf-8")
        first = inspect_ncaa_team_page(body, contract=self.contract)
        second = inspect_ncaa_team_page(body, contract=self.contract)
        self.assertEqual(first, second)
        self.assertEqual(1, first["legacy_schedule_record_count"])
        record = first["legacy_schedule_records"][0]
        self.assertEqual("AWAY", record["site_hint"])
        self.assertEqual("San Jose St.", record["opponent_display_name"])
        self.assertEqual("137345", record["opponent_team_season_id"])
        self.assertEqual(64, len(record["source_row_sha256"]))

    def test_team_graph_discovery_is_bounded_content_addressed_and_cache_reproducible(self) -> None:
        filler = "<div>NCAA official team statistics</div>" * 40

        def page(team_id: str, linked: str, contests: tuple[str, ...]) -> bytes:
            contest_links = "".join(f"<a href='/contests/{value}/box_score'>Game</a>" for value in contests)
            return (
                f"<html><body>NCAA<table><tr><td><a href='/teams/{team_id}'>Self</a>"
                f"<a href='/teams/{linked}'>Opponent</a>{contest_links}</td></tr></table>{filler}</body></html>"
            ).encode("utf-8")

        pages = {
            "https://stats.ncaa.org/teams/589027": page("589027", "589036", ("1", "2")),
            "https://stats.ncaa.org/teams/589036": page("589036", "589027", ("2", "3")),
        }

        class FakeBrowser:
            def __init__(self):
                self.calls = 0

            def fetch(self, uri):
                self.calls += 1
                return FetchResponse(body=pages[uri], status_code=200)

        with tempfile.TemporaryDirectory() as directory:
            store = RawSnapshotStore(Path(directory))
            first_browser = FakeBrowser()
            first = discover_season(
                season=2024,
                contract=self.contract,
                store=store,
                browser=first_browser,
                retrieved_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
                maximum_teams=10,
            )
            self.assertEqual("COMPLETE_GRAPH_EXHAUSTED", first["state"])
            self.assertEqual(2, first["discovered_team_count"])
            self.assertEqual(3, first["discovered_contest_count"])
            self.assertEqual(0, first["legacy_schedule_record_count"])
            self.assertEqual(2, first_browser.calls)
            second_browser = FakeBrowser()
            second = discover_season(
                season=2024,
                contract=self.contract,
                store=store,
                browser=second_browser,
                retrieved_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
                maximum_teams=10,
            )
            self.assertEqual(0, second_browser.calls)
            self.assertEqual(first["discovery_identity"], second["discovery_identity"])
            self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])

    def test_legacy_discovery_manifest_is_content_addressed_and_cache_reproducible(self) -> None:
        filler = "<div>NCAA official team statistics</div>" * 40
        body = (
            "<html><body>NCAA<table>"
            "<tr><td>09/04/2010</td><td><a href='/teams/137345'>@ San Jose St.</a></td>"
            "<td>W 48 - 3</td></tr>"
            f"</table>{filler}</body></html>"
        ).encode("utf-8")

        class FakeBrowser:
            def __init__(self):
                self.calls = 0

            def fetch(self, uri):
                self.calls += 1
                return FetchResponse(body=body, status_code=200)

        contract = json.loads(json.dumps(self.contract))
        contract["discovery"]["seed_team_season_ids"]["2010"] = "137345"
        with tempfile.TemporaryDirectory() as directory:
            store = RawSnapshotStore(Path(directory))
            first_browser = FakeBrowser()
            first = discover_season(
                season=2010,
                contract=contract,
                store=store,
                browser=first_browser,
                retrieved_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
                maximum_teams=10,
            )
            self.assertEqual("COMPLETE_GRAPH_EXHAUSTED", first["state"])
            self.assertEqual(1, first["legacy_schedule_record_count"])
            manifest = json.loads(Path(first["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual("1.1.0", manifest["schema_version"])
            self.assertEqual(1, manifest["legacy_schedule_record_count"])
            self.assertEqual(1, manifest["captures"][0]["legacy_schedule_record_count"])
            self.assertEqual(
                "SOURCE_LINKED_CANDIDATE_ONLY",
                manifest["captures"][0]["legacy_schedule_records"][0]["reconciliation_state"],
            )
            second_browser = FakeBrowser()
            second = discover_season(
                season=2010,
                contract=contract,
                store=store,
                browser=second_browser,
                retrieved_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
                maximum_teams=10,
            )
            self.assertEqual(0, second_browser.calls)
            self.assertEqual(first["discovery_identity"], second["discovery_identity"])
            self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])

    def test_discovery_route_cascade_uses_restored_proxies_without_exposing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "SCRAPFLY_API_TOKEN=OPTIONAL_LOCAL_SECRET_SCRAPFLY\n"
                "SCRAPERAPI_API_TOKEN=OPTIONAL_LOCAL_SECRET_SCRAPERAPI\n",
                encoding="utf-8",
            )
            routes, states = build_discovery_routes(
                contract=self.contract,
                env_file=env_file,
                browser=None,
                selected_route_ids=["scrapfly", "scraperapi"],
            )
            self.assertEqual(["scrapfly", "scraperapi"], [route_id for route_id, _ in routes])
            self.assertTrue(all(state["credential_state"] == "CONFIGURED_NONEMPTY" for state in states[-2:]))
            self.assertTrue(
                all(
                    route.timeout_seconds == float(self.contract["discovery"]["request_timeout_seconds"])
                    for _, route in routes
                )
            )
            serialized = json.dumps(states) + repr(routes)
            self.assertNotIn("OPTIONAL_LOCAL_SECRET_SCRAPFLY", serialized)
            self.assertNotIn("OPTIONAL_LOCAL_SECRET_SCRAPERAPI", serialized)

    def test_discovery_startup_falls_back_when_optional_patchright_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_file = root / ".env"
            env_file.write_text("", encoding="utf-8")
            expected = {
                "season": 2021,
                "state": "COMPLETE_GRAPH_EXHAUSTED",
                "discovery_identity": "a" * 64,
                "manifest_path": str(root / "manifest.json"),
                "manifest_sha256": "b" * 64,
                "team_page_capture_count": 1,
                "team_failure_count": 0,
                "discovered_team_count": 1,
                "discovered_contest_count": 1,
                "legacy_schedule_record_count": 0,
                "remaining_queue_count": 0,
            }
            arguments = [
                "--repo-root",
                str(ROOT),
                "--data-root",
                str(root / "data"),
                "--env-file",
                str(env_file),
                "--contract",
                str(self.contract_path),
                "--issued-at-utc",
                "2026-08-13T00:00:00Z",
                "--runtime-root",
                str(root / "runtime"),
                "--discover-season",
                "2021",
                "--discovery-only",
                "--discovery-route-id",
                "direct_http",
                "--discovery-route-id",
                "local_patchright_chrome",
            ]
            with (
                patch.object(sys, "argv", ["acquire_ncaa_official_gamebooks.py", *arguments]),
                patch(
                    "acquire_ncaa_official_gamebooks.select_browser_runtime",
                    return_value=(Path("chrome.exe"), None),
                ),
                patch(
                    "acquire_ncaa_official_gamebooks.StatefulPatchrightSession.__enter__",
                    side_effect=ImportError("patchright absent"),
                ),
                patch("acquire_ncaa_official_gamebooks.discover_season", return_value=expected) as discovery,
            ):
                self.assertEqual(0, main())
            self.assertEqual(["direct_http"], [route_id for route_id, _ in discovery.call_args.kwargs["routes"]])

    def test_request_identity_is_stable_and_canonical_identity_remains_unpromoted(self) -> None:
        contest = self.contract["seed_contests"][0]
        endpoint = self.contract["endpoints"][0]
        first = request_for(self.contract, contest, endpoint)
        second = request_for(self.contract, dict(contest), dict(endpoint))
        self.assertEqual(first.identity_sha256, second.identity_sha256)
        self.assertIsNone(contest["canonical_game_id"])
        self.assertIn("RECONCILIATION_PENDING", contest["identity_state"])
        self.assertNotIn("key", first.source_uri.lower())
        self.assertNotIn("token", first.source_uri.lower())

    def test_reconciled_contest_manifest_drives_candidate_only_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            core = {
                "season": 2022,
                "mapping_records": [
                    {
                        "ncaa_contest_id": "2276460",
                        "canonical_game_id": "game_1",
                        "canonical_home_team_id": "team_home",
                        "canonical_away_team_id": "team_away",
                        "canonical_start_utc": "2022-08-28T02:00:00Z",
                        "season": 2022,
                        "season_type": "regular",
                        "mapping_method": "TWO_SIDED_EXACT_PARTICIPANTS_DATE_SCORE_CONTEXT",
                        "name_only_promotion": False,
                        "historical_pit_eligible": False,
                        "training_eligible": False,
                        "protected_eligible": False,
                    }
                ],
            }
            identity = __import__("hashlib").sha256(
                json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            manifest = {
                "dataset_identity": identity,
                "identity_core": core,
                "authority": {
                    "canonical_registry_write": False,
                    "historical_pit_eligible": False,
                    "training_eligible": False,
                    "protected_evaluation_eligible": False,
                    "production_eligible": False,
                },
            }
            path = data_root / "manifests/ncaa_contest_reconciliation/sha256" / identity / "run_manifest.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(manifest), encoding="utf-8")

            contests, evidence = load_reconciled_contests(path, data_root)

            self.assertEqual("2276460", contests[0]["contest_id"])
            self.assertEqual("game_1", contests[0]["canonical_game_id"])
            self.assertEqual("EXACT_TWO_SIDED_CONTEXT_RECONCILED_CANDIDATE_ONLY", contests[0]["identity_state"])
            self.assertEqual(identity, evidence["dataset_identity"])
            self.assertIn("NO_PIT_TRAINING_PROTECTED", evidence["authority"])

    def test_reconciled_contest_manifest_rejects_name_only_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            core = {
                "season": 2022,
                "mapping_records": [
                    {
                        "ncaa_contest_id": "1",
                        "canonical_game_id": "game_1",
                        "canonical_home_team_id": "home",
                        "canonical_away_team_id": "away",
                        "canonical_start_utc": "2022-01-01T00:00:00Z",
                        "season": 2022,
                        "season_type": "regular",
                        "mapping_method": "TWO_SIDED_EXACT_PARTICIPANTS_DATE_SCORE_CONTEXT",
                        "name_only_promotion": True,
                        "historical_pit_eligible": False,
                        "training_eligible": False,
                        "protected_eligible": False,
                    }
                ],
            }
            identity = __import__("hashlib").sha256(
                json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            path = data_root / "manifests/ncaa_contest_reconciliation/sha256" / identity / "run_manifest.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "dataset_identity": identity,
                        "identity_core": core,
                        "authority": {
                            "canonical_registry_write": False,
                            "historical_pit_eligible": False,
                            "training_eligible": False,
                            "protected_evaluation_eligible": False,
                            "production_eligible": False,
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "name-only"):
                load_reconciled_contests(path, data_root)

    def test_dotenv_loader_returns_only_requested_value_and_rejects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OTHER=do-not-return\nSCRAPFLY_API_TOKEN='configured'\n", encoding="utf-8")
            self.assertEqual("configured", load_optional_dotenv_value(path, "SCRAPFLY_API_TOKEN"))
            self.assertIsNone(load_optional_dotenv_value(path, "SCRAPERAPI_API_TOKEN"))
            path.write_text("SCRAPFLY_API_TOKEN=one\nSCRAPFLY_API_TOKEN=two\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "more than once"):
                load_optional_dotenv_value(path, "SCRAPFLY_API_TOKEN")

    def test_proxy_credentials_are_nonempty_and_absent_from_repr(self) -> None:
        direct = DirectHTTPTransport()
        scrapfly = ScrapflyTransport("scrapfly-secret")
        scraperapi = ScraperAPITransport("scraperapi-secret")
        self.assertNotIn("secret", repr(scrapfly))
        self.assertNotIn("secret", repr(scraperapi))
        self.assertNotIn("token", repr(direct).lower())
        with self.assertRaises(ValueError):
            ScrapflyTransport("")
        with self.assertRaises(ValueError):
            ScraperAPITransport("")

    def test_route_builder_skips_empty_proxy_credentials_without_blocking_local_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_file = root / ".env"
            env_file.write_text("SCRAPFLY_API_TOKEN=\nSCRAPERAPI_API_TOKEN=\n", encoding="utf-8")
            routes, states = build_routes(
                contract=self.contract,
                env_file=env_file,
                runtime_root=root,
                contest_id="5362283",
                endpoint_id="box_score",
            )
            route_ids = [row[0] for row in routes]
            state_by_id = {row["route_id"]: row for row in states}
            self.assertIn("direct_http", route_ids)
            self.assertNotIn("scrapfly", route_ids)
            self.assertNotIn("scraperapi", route_ids)
            self.assertEqual("EMPTY_OR_ABSENT", state_by_id["scrapfly"]["credential_state"])
            self.assertEqual("EMPTY_OR_ABSENT", state_by_id["scraperapi"]["credential_state"])

    def test_immutable_capture_caches_same_request_without_refetch(self) -> None:
        contest = self.contract["seed_contests"][0]
        endpoint = self.contract["endpoints"][0]
        request = request_for(self.contract, contest, endpoint)
        body = self.fixture("box_score", "Box Score and Team Statistics")
        calls = {"count": 0}

        def fetch(_request):
            calls["count"] += 1
            return FetchResponse(body=body, status_code=200)

        transport = ValidatingTransport(fetch, "5362283", "box_score", self.contract)
        with tempfile.TemporaryDirectory() as directory:
            store = RawSnapshotStore(Path(directory))
            first = acquire_one(
                store=store,
                request=request,
                routes=[("fixture", transport)],
                retrieved_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
                maximum_attempts=1,
            )
            second = acquire_one(
                store=store,
                request=request,
                routes=[("fixture", transport)],
                retrieved_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
                maximum_attempts=1,
            )
            self.assertEqual(1, calls["count"])
            self.assertEqual("CAPTURED", first["state"])
            self.assertTrue(second["from_cache"])
            self.assertEqual(first["snapshot_id"], second["snapshot_id"])
            self.assertEqual(first["raw_sha256"], second["raw_sha256"])

    def test_gate_preserves_partial_success_without_claiming_scaleout_or_pit(self) -> None:
        manifest = {
            "acquisition_identity": "a" * 64,
            "request_count": 2,
            "captured_count": 1,
            "technical_failure_count": 1,
            "domain_capture_counts": {"play_by_play": 1},
            "selection_evidence": {
                "source": "RECONCILED_CONTEST_CANDIDATES",
                "dataset_identity": "c" * 64,
            },
            "captures": [
                {"state": "CAPTURED", "contest_id": "5362283", "endpoint_id": "play_by_play"},
                {"state": "TECHNICALLY_UNAVAILABLE", "contest_id": "5362283", "endpoint_id": "officials"},
            ],
        }
        gate = build_gate(
            contract=self.contract,
            manifest=manifest,
            manifest_path=Path("external/manifest.json"),
            manifest_sha256="b" * 64,
        )
        self.assertEqual("PASS_BOUNDED_CANDIDATE_CAPTURE", gate["result"])
        self.assertFalse(gate["identity_gate"]["canonical_game_identity_promoted"])
        self.assertFalse(gate["pit_gate"]["historical_pit_eligible"])
        self.assertFalse(gate["scale_out_gate"]["automatic_national_scale_out_enabled"])
        self.assertIn("officials", gate["bounded_population"]["missing_domains"])
        self.assertEqual(
            "c" * 64,
            gate["bounded_population"]["selection_evidence"]["dataset_identity"],
        )

    @unittest.skipUnless(importlib.util.find_spec("sportsdataverse"), "pinned parser runtime is optional")
    def test_pinned_parsers_normalize_every_domain_without_identity_or_pit_promotion(self) -> None:
        fixtures = {
            "box_score": """
                <html><table><tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th><th>S</th></tr>
                <tr><td>Away</td><td>7</td><td>0</td><td>3</td><td>0</td><td>10</td></tr>
                <tr><td>Home</td><td>0</td><td>7</td><td>7</td><td>7</td><td>21</td></tr>
                <tr><td>09/07/2024</td></tr><tr><td>Example Stadium (Town)</td></tr>
                <tr><td>Attendance: 12,345</td></tr></table></html>""",
            "drives": """
                <html><table id='public_game_drives_data_table'><tr><th>No</th></tr>
                <tr><td>1</td><td>1</td><td>Away</td><td>1</td><td>KO</td><td>15:00</td><td>AWY25</td><td>1</td><td>PUNT</td><td>12:00</td><td>HOM40</td></tr>
                </table></html>""",
            "team_stats": """
                <html><table id='rankings_table'><tr><td>Team Stats</td><td>Away</td><td>Home</td></tr>
                <tr><td>Rushing</td></tr><tr><td>Yards</td><td>100</td><td>120</td></tr></table></html>""",
            "individual_stats": """
                <html><table id='competitor_10_year_stat_category_20_data_table'>
                <tr><th>#</th><th>Name</th><th>P</th><th>Rush Attempts</th><th>Yds/Rush</th></tr>
                <tr><td>1</td><td>Doe,John</td><td>RB</td><td>10</td><td>5.0</td></tr></table></html>""",
            "officials": """
                <html><table><tr><th>Role</th><th>Official</th></tr>
                <tr><td>Referee</td><td>Jane Official</td></tr></table></html>""",
            "play_by_play": """
                <html><div class='drives'>
                <h5 class='non_scoring_play'>AWY PUNT 10:00,AWY25, 1 play, 5 yards, 1:00 0 - 0</h5>
                <div class='non_scoring_play'><div><span>1st &amp; 10 at AWY25</span>
                <span>(10:00) Doe,John rush for 5 yards gain to the AWY30</span></div></div>
                </div></html>""",
        }
        expected_domains = {
            "box_score": {"linescore_game_info", "venue", "attendance"},
            "drives": {"drives"},
            "team_stats": {"team_stats_by_period"},
            "individual_stats": {"player_stats"},
            "officials": {"officials"},
            "play_by_play": {"play_by_play"},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for endpoint_id, source in fixtures.items():
                raw_path = root / f"{endpoint_id}.html"
                raw_path.write_text(source, encoding="utf-8")
                outputs = normalize_ncaa_capture(
                    raw_path=raw_path,
                    raw_sha256="a" * 64,
                    contest_id="5362283",
                    endpoint_id=endpoint_id,
                    source_uri=f"https://stats.ncaa.org/contests/5362283/{endpoint_id}",
                    retrieved_at_utc="2026-08-12T00:00:00Z",
                    contract=self.contract,
                    data_root=root,
                )
                self.assertEqual(expected_domains[endpoint_id], {row["domain"] for row in outputs})
                self.assertTrue(all(row["state"] == "PARSED_CANDIDATE" for row in outputs))
                for output in outputs:
                    payload = json.loads((root / output["payload_relative_path"]).read_text(encoding="utf-8"))
                    self.assertFalse(payload["historical_pit_eligible"])
                    self.assertFalse(payload["canonical_identity_promoted"])
                    self.assertEqual(self.contract["source"]["upstream_parser_commit"], payload["parser"]["repository_commit"])


if __name__ == "__main__":
    unittest.main()
