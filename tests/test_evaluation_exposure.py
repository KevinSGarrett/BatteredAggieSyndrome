from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.validation.evaluation_exposure import (  # noqa: E402
    EXPOSED_STATUS,
    canonical_json,
    discover_exposed_runs,
    validate_claims,
    validate_ledger,
)
from aggie_analytics.validation.retraining_admission import decide, validate_decision  # noqa: E402


class ExposureAwareEvaluationTests(unittest.TestCase):
    def _ledger(self, source: Path) -> dict:
        record = {
            "source_manifest_path": str(source),
            "source_manifest_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "run_identity": "r" * 64,
            "dataset_identity": "d" * 64,
            "feature_identity": "f" * 64,
            "target_identity": "t" * 64,
            "split_identity": "s" * 64,
            "forecast_identity": None,
            "model_identities": ["m" * 64],
            "exposed_seasons": [2024, 2025],
            "decision_families": ["ELO_REFERENCE_AND_CHALLENGER_STRATEGY"],
            "feedback_channels": ["MODEL_COMPARISON"],
            "prompt_identities": [],
            "prompt_disposition": "NOT_APPLICABLE_DETERMINISTIC_PRELIMINARY_RUN",
            "eligibility": EXPOSED_STATUS,
        }
        ledger = {
            "schema_version": "1.0.0",
            "artifact_type": "EVALUATION_CONTAMINATION_EXPOSURE_LEDGER",
            "records": [record],
        }
        ledger["ledger_identity"] = hashlib.sha256(canonical_json(ledger)).hexdigest()
        return ledger

    def test_exposed_artifact_cannot_claim_untouched_protected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "run_manifest.json"
            source.write_text("{}", encoding="utf-8")
            ledger = self._ledger(source)
            self.assertEqual(validate_ledger(ledger), [])
            claims = [{"artifact_identity": "m" * 64, "evaluation_status": "UNTOUCHED_PROTECTED"}]
            self.assertEqual(validate_claims(claims, ledger), ["claim[0]:exposed_as_untouched_protected"])
            claims[0]["evaluation_status"] = EXPOSED_STATUS
            self.assertEqual(validate_claims(claims, ledger), [])
            inherited = [{"artifact_identity": "new", "derived_from": ["m" * 64], "evaluation_status": "PROTECTED_PROMOTION_ELIGIBLE"}]
            self.assertEqual(validate_claims(inherited, ledger), ["claim[0]:exposed_as_untouched_protected"])

    def test_discovers_only_preliminary_runs_with_exposed_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "manifests/preliminary_demo/sha256/abc/run_manifest.json"
            run.parent.mkdir(parents=True)
            run.write_text(
                '{"classification":"PRELIMINARY_UNPROTECTED","run_identity":"abc","metrics":{"SEASON_2025_ALL":{"brier":0.2}},"models":[]}',
                encoding="utf-8",
            )
            records = discover_exposed_runs(root)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["exposed_seasons"], [2025])

    def test_retraining_requires_evidence_backed_material_change(self):
        request = {
            "old_dataset_identity": "a" * 64,
            "new_dataset_identity": "b" * 64,
            "training_eligible": True,
            "observed_deltas": {"eligible_games": 100},
            "material_changes": [{"kind": "ADDITIONAL_ELIGIBLE_SEASONS_OR_GAMES", "material": True, "evidence_identity": "e" * 64, "rationale": "One complete eligible season was added."}],
        }
        decision = decide(request)
        self.assertEqual(decision["action"], "FULL_LADDER_RETRAINING_ADMITTED")
        self.assertEqual(validate_decision(decision), [])
        request["material_changes"][0]["evidence_identity"] = ""
        self.assertEqual(decide(request)["action"], "REJECT_INVALID_EVIDENCE")

    def test_candidate_only_population_gets_focused_replay(self):
        request = {
            "old_dataset_identity": "a" * 64,
            "new_dataset_identity": "b" * 64,
            "training_eligible": False,
            "observed_deltas": {"candidate_games": 1000},
            "material_changes": [{"kind": "ADDITIONAL_ELIGIBLE_SEASONS_OR_GAMES", "material": True, "evidence_identity": "e" * 64, "rationale": "Candidate-only official evidence was added."}],
        }
        self.assertEqual(decide(request)["action"], "FOCUSED_INTEGRATION_REPLAY_ONLY")

    def test_elo_replay_batches_target_games_before_updates(self):
        spec = importlib.util.spec_from_file_location("elo_challengers", ROOT / "tools" / "run_preliminary_elo_challengers.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        rows = [
            {"target_game_id": "g1", "season": 2023, "season_type": "regular", "week": 1, "start_utc": "2023-09-01T00:00:00Z", "home_team_id": "a", "away_team_id": "b", "neutral_site": True, "home_win": 1.0, "margin": 7, "cold_start": True},
            {"target_game_id": "g2", "season": 2023, "season_type": "regular", "week": 1, "start_utc": "2023-09-02T00:00:00Z", "home_team_id": "a", "away_team_id": "b", "neutral_site": True, "home_win": 0.0, "margin": -7, "cold_start": True},
        ]
        replayed = module.replay(rows, offseason_retention=1.0, margin_cap=None)
        self.assertEqual([row["home_win_probability"] for row in replayed], [0.5, 0.5])
        self.assertEqual(replayed, module.replay(rows, offseason_retention=1.0, margin_cap=None))


if __name__ == "__main__":
    unittest.main()
