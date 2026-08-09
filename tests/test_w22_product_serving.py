from __future__ import annotations

import ast
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.api import create_app
from aggie_analytics.orchestration import ImmutableForecastPublisher
from aggie_analytics.product import (
    ForecastProductService,
    FreshnessPolicy,
    PublishedSnapshotRepository,
    SNAPSHOT_SCHEMA_V1,
)
from aggie_analytics.product.dashboard import dashboard_view_model

UTC = timezone.utc
CUTOFF = datetime(2026, 8, 1, 18, 0, tzinfo=UTC)
PUBLISHED = datetime(2026, 8, 1, 18, 5, tzinfo=UTC)


def payload(*, snapshot_id: str = "fri-1", lane: str = "PURE_FOOTBALL", cutoff: datetime = CUTOFF, published: datetime = PUBLISHED) -> dict:
    return {
        "schema_version": "aggie.forecast.snapshot.v2",
        "snapshot_id": snapshot_id,
        "game_id": "tamu-lsu-2026",
        "forecast_cutoff": cutoff.isoformat(),
        "published_at": published.isoformat(),
        "model_artifact_sha256": "model-sha-synthetic",
        "feature_snapshot_id": "feature-snapshot-synthetic",
        "market_lane": lane,
        "teams": {"team_name": "Texas A&M", "opponent_name": "LSU"},
        "public_summary": {
            "win_probability": 0.61,
            "loss_probability": 0.39,
            "expected_team_score": 28.0,
            "expected_opponent_score": 24.0,
            "expected_margin": 4.0,
            "bas_ge_3": 0.31,
            "bas_ge_7": 0.18,
        },
        "lineage_refs": ["raw:synthetic", "pit:synthetic", "feature:synthetic"],
        "data_snapshot_refs": ["data:snapshot:synthetic"],
        "uncertainty": [{"kind": "MODEL_DISAGREEMENT", "level": "SYNTHETIC"}],
        "warnings": ["SYNTHETIC_FIXTURE_ONLY"],
        "availability": [{"player": "QB1", "state": "QUESTIONABLE", "evidence": "synthetic"}],
        "matchup_explanation": [{"driver": "pass_efficiency_matchup", "direction": "A&M", "scope": "synthetic"}],
        "historical_analogs": [{"game_id": "synthetic-analog", "similarity": 0.72}],
        "source_metadata": [{"source_id": "SRC-SYNTHETIC", "capture_ref": "raw:synthetic"}],
        "model_metadata": {"model_family": "SYNTHETIC_ONLY", "training_cutoff": "2026-07-31T00:00:00+00:00"},
        "comparison_context": {"national_reference_win_probability": 0.60, "tamu_specialization_adjustment": "SYNTHETIC_ONLY"},
        "public_metadata": {"fixture_kind": "SYNTHETIC_W22_TEST"},
    }


def write_payload(root: Path, item: dict) -> Path:
    game = root / item["game_id"]
    game.mkdir(parents=True, exist_ok=True)
    path = game / f"{item['snapshot_id']}-{item['market_lane']}.json"
    path.write_text(json.dumps(item, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class W22ProductServingTests(unittest.TestCase):
    def test_v1_published_snapshot_remains_readable(self):
        with tempfile.TemporaryDirectory() as td:
            item = payload()
            item.pop("schema_version")
            item.pop("market_lane")
            for key in ("uncertainty", "warnings", "availability", "matchup_explanation", "historical_analogs", "source_metadata", "model_metadata", "data_snapshot_refs", "comparison_context", "public_metadata", "teams"):
                item.pop(key, None)
            write_payload(Path(td), {**item, "market_lane": "PURE_FOOTBALL"})
            # Remove the lane field after filename creation to emulate the W21 payload.
            path = next((Path(td) / "tamu-lsu-2026").glob("*.json"))
            old = json.loads(path.read_text(encoding="utf-8")); old.pop("market_lane", None)
            path.write_text(json.dumps(old), encoding="utf-8")
            snapshot = PublishedSnapshotRepository(Path(td)).latest("tamu-lsu-2026", as_of=PUBLISHED + timedelta(hours=1))
            self.assertEqual(SNAPSHOT_SCHEMA_V1, snapshot.schema_version)
            self.assertEqual("PURE_FOOTBALL", snapshot.market_lane)

    def test_repository_latest_is_chronological_and_as_of_safe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_payload(root, payload(snapshot_id="mon", cutoff=CUTOFF - timedelta(days=4), published=PUBLISHED - timedelta(days=4)))
            write_payload(root, payload(snapshot_id="fri", cutoff=CUTOFF, published=PUBLISHED))
            write_payload(root, payload(snapshot_id="future", cutoff=CUTOFF + timedelta(days=1), published=PUBLISHED + timedelta(days=1)))
            repo = PublishedSnapshotRepository(root)
            self.assertEqual("fri", repo.latest("tamu-lsu-2026", as_of=PUBLISHED + timedelta(hours=1)).snapshot_id)
            self.assertEqual("mon", repo.latest("tamu-lsu-2026", as_of=PUBLISHED - timedelta(days=2)).snapshot_id)

    def test_repository_rejects_untrusted_game_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_payload(root, payload())
            repo = PublishedSnapshotRepository(root)
            for game_id in ("", ".", "..", "../outside", "..\\outside", "/outside", "C:", "bad name", "x" * 129):
                with self.subTest(game_id=game_id), self.assertRaises(ValueError):
                    repo.list_snapshots(game_id)
            self.assertEqual((), repo.list_snapshots("missing-safe-id"))

    def test_repository_rejects_symlinked_game_directory(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "published"
            outside = base / "outside"
            root.mkdir()
            write_payload(outside, payload())
            link = root / "tamu-lsu-2026"
            try:
                link.symlink_to(outside / "tamu-lsu-2026", target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            repo = PublishedSnapshotRepository(root)
            with self.assertRaisesRegex(ValueError, "unsafe game repository entry"):
                repo.list_snapshots("tamu-lsu-2026")

    def test_pure_and_market_lanes_remain_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pure = payload(snapshot_id="fri-pure", lane="PURE_FOOTBALL")
            market = payload(snapshot_id="fri-market", lane="MARKET_AUGMENTED")
            market["public_summary"]["win_probability"] = 0.64
            market["public_summary"]["loss_probability"] = 0.36
            write_payload(root, pure); write_payload(root, market)
            service = ForecastProductService(PublishedSnapshotRepository(root))
            now = PUBLISHED + timedelta(hours=1)
            self.assertEqual(0.61, service.forecast("tamu-lsu-2026", market_lane="PURE_FOOTBALL", now=now)["forecast"]["win_probability"])
            self.assertEqual(0.64, service.forecast("tamu-lsu-2026", market_lane="MARKET_AUGMENTED", now=now)["forecast"]["win_probability"])

    def test_freshness_never_claims_current_without_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); write_payload(root, payload())
            service = ForecastProductService(PublishedSnapshotRepository(root), FreshnessPolicy())
            response = service.forecast("tamu-lsu-2026", now=PUBLISHED + timedelta(hours=3))
            self.assertEqual("UNASSESSED_THRESHOLD_TBD", response["freshness"]["state"])
            self.assertIsNone(response["freshness"]["stale"])
            self.assertIn("FRESHNESS_THRESHOLD_NOT_OPERATIONALLY_FROZEN", response["warnings"])

    def test_configured_freshness_marks_stale_visibly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); write_payload(root, payload())
            service = ForecastProductService(PublishedSnapshotRepository(root), FreshnessPolicy(timedelta(hours=2)))
            response = service.forecast("tamu-lsu-2026", now=PUBLISHED + timedelta(hours=5))
            self.assertEqual("STALE", response["freshness"]["state"])
            self.assertTrue(response["freshness"]["stale"])
            self.assertIn("FORECAST_STALE_AT_SERVE_TIME", response["warnings"])

    def test_forecast_view_exposes_product_context_and_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); write_payload(root, payload())
            service = ForecastProductService(PublishedSnapshotRepository(root), FreshnessPolicy(timedelta(days=1)))
            response = service.forecast("tamu-lsu-2026", now=PUBLISHED + timedelta(hours=1))
            self.assertEqual("IMMUTABLE_PUBLISHED_SNAPSHOT_ONLY", response["serving_mode"])
            self.assertEqual(0.18, response["bas"]["ge_7"])
            self.assertEqual("PRECOMPUTED_ASSOCIATIONAL_NOT_CAUSAL", response["explainability"]["claim_scope"])
            self.assertTrue(response["uncertainty"])
            self.assertTrue(response["explainability"]["availability"])
            self.assertTrue(response["explainability"]["matchup_drivers"])
            self.assertTrue(response["explainability"]["historical_analogs"])
            self.assertEqual("model-sha-synthetic", response["lineage"]["model_artifact_sha256"])
            self.assertEqual(["data:snapshot:synthetic"], response["lineage"]["data_snapshot_refs"])

    def test_dashboard_view_model_contains_required_surfaces(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); write_payload(root, payload())
            service = ForecastProductService(PublishedSnapshotRepository(root), FreshnessPolicy(timedelta(days=1)))
            view = dashboard_view_model(service, "tamu-lsu-2026", now=PUBLISHED + timedelta(hours=1))
            for key in ("headline", "bas", "uncertainty", "freshness", "availability", "matchup_drivers", "historical_analogs", "comparison_context", "lineage"):
                self.assertIn(key, view)
            self.assertEqual("Texas A&M vs LSU", view["title"])

    def test_serving_packages_do_not_import_training_or_data_internals(self):
        repo_root = Path(__file__).resolve().parents[1]
        forbidden = ("aggie_analytics.data", "aggie_analytics.features", "aggie_analytics.modeling", "aggie_analytics.experimentation", "aggie_analytics.team_state")
        for base in (repo_root / "src/aggie_analytics/product", repo_root / "src/aggie_analytics/api"):
            for path in base.glob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
                    if isinstance(node, ast.ImportFrom) and node.module: imports.append(node.module)
                self.assertFalse([name for name in imports if name.startswith(forbidden)], f"forbidden serving import in {path}")

    def test_fastapi_adapter_is_lazy_optional_dependency(self):
        # Importing the adapter must not require FastAPI; create_app imports it only at call time.
        self.assertTrue(callable(create_app))
        pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('[project.optional-dependencies]', pyproject)
        self.assertIn('product = [', pyproject)
        self.assertIn('fastapi', pyproject)
        self.assertIn('uvicorn', pyproject)
        self.assertIn('dependencies = []', pyproject)

    def test_w21_publisher_signature_remains_compatible_and_v2_extensions_are_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pub = ImmutableForecastPublisher(root)
            cutoff = datetime.now(UTC) - timedelta(hours=1)
            base = dict(snapshot_id="pub-1", game_id="g1", forecast_cutoff=cutoff, model_artifact_sha256="m", feature_snapshot_id="f", public_summary={"win_probability": .5, "loss_probability": .5}, lineage_refs=("raw", "pit", "feat"))
            first = pub.publish(**base)
            self.assertEqual(first, pub.publish(**base))
            with self.assertRaises(RuntimeError):
                pub.publish(**{**base, "market_lane": "MARKET_AUGMENTED"})
            loaded = PublishedSnapshotRepository(root).latest("g1", as_of=datetime.now(UTC) + timedelta(minutes=1))
            self.assertEqual("aggie.forecast.snapshot.v2", loaded.schema_version)

    def test_static_dashboard_contains_required_sections(self):
        root = Path(__file__).resolve().parents[1] / "src/aggie_analytics/product/static"
        html = (root / "index.html").read_text(encoding="utf-8")
        for phrase in ("BAS severity", "Uncertainty", "Player availability", "Matchup drivers", "Historical analogs", "Forecast provenance"):
            self.assertIn(phrase, html)

    def test_w21_validator_is_forward_compatible(self):
        from tools.validate_w21_mlops import validate
        self.assertEqual([], validate(Path(__file__).resolve().parents[1]))


if __name__ == "__main__":
    unittest.main()
