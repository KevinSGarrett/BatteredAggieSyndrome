from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from aggie_analytics.data.historical_game_outcome_spine import _validate_contract_authority
from aggie_analytics.data.historical_game_outcome_spine_expansion import (
    _deep_merge,
    resolve_expansion_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/historical_game_outcome_spine_expansion_contract.json"


class HistoricalGameOutcomeSpineExpansionTests(unittest.TestCase):
    def test_contract_resolves_from_pinned_base(self) -> None:
        contract, sources = resolve_expansion_contract(
            repo_root=ROOT, contract_path=CONTRACT
        )
        self.assertEqual(contract["decision_unit"], "POST-SUBTASK-197")
        self.assertEqual(contract["jira_key"], "BAT-554")
        self.assertEqual(contract["source_contract"]["source_seasons"], list(range(1963, 2026)))
        self.assertEqual(contract["acceptance"]["expected_completed_outcomes"], 46957)
        self.assertEqual(contract["acceptance"]["expected_schedule_only_nonoutcomes"], 3)
        self.assertEqual(sources["base_relative_path"], "configs/historical_game_outcome_spine_contract.json")
        _validate_contract_authority(contract)

    def test_base_hash_drift_fails_closed(self) -> None:
        overlay = json.loads(CONTRACT.read_text(encoding="utf-8"))
        overlay["base_contract_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "overlay.json"
            path.write_text(json.dumps(overlay), encoding="utf-8")
            with self.assertRaises(ValueError):
                resolve_expansion_contract(repo_root=ROOT, contract_path=path)

    def test_deep_merge_does_not_mutate_base(self) -> None:
        base = {"source": {"season": 2009, "nested": {"a": 1}}, "keep": True}
        merged = _deep_merge(base, {"source": {"season": 2025, "nested": {"b": 2}}})
        self.assertEqual(base["source"]["season"], 2009)
        self.assertEqual(merged["source"], {"season": 2025, "nested": {"a": 1, "b": 2}})
        self.assertTrue(merged["keep"])

    def test_2024_2025_are_not_untouched_protected(self) -> None:
        contract, _ = resolve_expansion_contract(repo_root=ROOT, contract_path=CONTRACT)
        findings = " ".join(contract["negative_findings"])
        self.assertIn("2024-2025", findings)
        self.assertIn("not represented as untouched protected", findings)
        self.assertFalse(contract["authority"]["protected_evaluation_admission"])


if __name__ == "__main__":
    unittest.main()
