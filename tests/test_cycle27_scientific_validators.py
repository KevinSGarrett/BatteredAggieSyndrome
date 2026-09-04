"""Cycle 27 non-vacuous scientific validator regressions."""

from __future__ import annotations

import ast
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from aggie_analytics.scientific_reference.coherence import pair_normalize  # noqa: E402
from tools.validate_cross_output_coherence import (  # noqa: E402
    validate_payload as validate_cross_payload,
)
from tools.validate_independent_scientific_reference import (  # noqa: E402
    validate as validate_independence,
)
from tools.validate_raw_to_forecast_trace import (  # noqa: E402
    validate_payload as validate_trace_payload,
)


def _coherent_row(
    *, game: str = "g1", candidate: str = "ridge", checkpoint: str = "T24"
) -> dict:
    return {
        "opportunity_id": f"{candidate}|{game}|{checkpoint}",
        "candidate_id": candidate,
        "canonical_game_id": game,
        "checkpoint_id": checkpoint,
        "home_win_probability": 0.6,
        "away_win_probability": 0.4,
        "expected_margin_home": 3.0,
        "expected_margin_away": -3.0,
        "schema_version": "aggie.shadow.cycle27.v1",
        "child_sha256": "a" * 64,
    }


class Cycle27ScientificValidators(unittest.TestCase):
    def test_empty_list_is_not_empty_universe_authority(self) -> None:
        findings = validate_cross_payload({"rows": [], "expected_opportunity_ids": []})
        self.assertIn("CROSS_OUTPUT_EMPTY_COHORT_WITHOUT_AUTHORITY", findings)
        trace = validate_trace_payload({"traces": [], "expected_opportunity_ids": []})
        self.assertIn("TRACE_EMPTY_COHORT_WITHOUT_AUTHORITY", trace)

    def test_independent_empty_universe_authority_may_be_empty(self) -> None:
        authority = {
            "empty_universe_authorized": True,
            "independent_source_identity": "PINNED_EMPTY_CONTRACT_V1",
        }
        findings = validate_cross_payload(
            {
                "rows": [],
                "expected_opportunity_ids": [],
                "empty_universe_authority": authority,
            }
        )
        self.assertEqual([], findings)

    def test_invalid_probabilities_are_not_normalized(self) -> None:
        result = pair_normalize(2.0, 3.0, 1.0, -1.0)
        self.assertFalse(result["coherent"])
        self.assertEqual(result["abstain_reason"], "ABSTAIN_PROBABILITY_OUT_OF_RANGE")
        findings = validate_cross_payload(
            {
                "expected_opportunity_ids": ["ridge|g1|T24"],
                "rows": [
                    {
                        **_coherent_row(),
                        "home_win_probability": 2.0,
                        "away_win_probability": 3.0,
                    }
                ],
            }
        )
        self.assertTrue(any("INVALID_P_NOT_NORMALIZABLE" in item for item in findings))
        self.assertTrue(
            any("INCOHERENT" in item or "OUT_OF_RANGE" in item for item in findings)
        )

    def test_membership_duplicates_and_hidden_abstention(self) -> None:
        row = _coherent_row()
        findings = validate_cross_payload(
            {
                "expected_opportunity_ids": ["ridge|g1|T24", "ridge|g2|T24"],
                "rows": [row, dict(row)],
            }
        )
        self.assertTrue(any("DUPLICATE_KEY" in item for item in findings))
        self.assertTrue(any("UNACCOUNTED" in item for item in findings))
        hidden = validate_cross_payload(
            {
                "expected_opportunity_ids": ["ridge|g1|T24"],
                "rows": [
                    {
                        **row,
                        "abstained": True,
                        "abstain_reason": "ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED",
                        "home_win_probability": 0.91,
                        "away_win_probability": 0.09,
                    }
                ],
            }
        )
        self.assertTrue(any("ABSTENTION_HIDDEN_P" in item for item in hidden))

    def test_future_known_at_fake_hash_and_raw_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw.bin"
            raw.write_bytes(b"official-bytes")
            digest = hashlib.sha256(b"official-bytes").hexdigest()
            future = validate_trace_payload(
                {
                    "expected_opportunity_ids": ["ridge|g1|T24"],
                    "as_of_utc": "2026-09-04T16:00:00Z",
                    "traces": [
                        {
                            "opportunity_id": "ridge|g1|T24",
                            "candidate_id": "ridge",
                            "canonical_game_id": "g1",
                            "checkpoint_id": "T24",
                            "raw_source_identity": "ncaa",
                            "raw_sha256": digest,
                            "raw_bytes_path": "raw.bin",
                            "feature_row_identity": "f1",
                            "forecast_row_identity": "p1",
                            "known_at_utc": "2026-09-04T18:00:00Z",
                            "cutoff_utc": "2026-09-04T16:00:00Z",
                            "current_opponent_key": "MSU",
                            "trust_classification": "UNTRUSTED_SHADOW",
                        }
                    ],
                },
                data_root=root,
            )
            self.assertTrue(any("FUTURE_KNOWN_AT" in item for item in future))
            fake = validate_trace_payload(
                {
                    "expected_opportunity_ids": ["g1"],
                    "traces": [
                        {
                            "raw_source_identity": "ncaa",
                            "raw_sha256": "0" * 64,
                            "canonical_game_id": "g1",
                            "feature_row_identity": "f1",
                            "forecast_row_identity": "p1",
                            "known_at_utc": "2026-09-04T12:00:00Z",
                            "cutoff_utc": "2026-09-04T16:00:00Z",
                            "current_opponent_key": "MSU",
                            "trust_classification": "UNTRUSTED_SHADOW",
                        }
                    ],
                }
            )
            self.assertTrue(any("FAKE_HASH" in item for item in fake))
            mismatch = validate_trace_payload(
                {
                    "expected_opportunity_ids": ["g1"],
                    "traces": [
                        {
                            "raw_source_identity": "ncaa",
                            "raw_sha256": hashlib.sha256(b"other").hexdigest(),
                            "raw_bytes_path": "raw.bin",
                            "canonical_game_id": "g1",
                            "feature_row_identity": "f1",
                            "forecast_row_identity": "p1",
                            "known_at_utc": "2026-09-04T12:00:00Z",
                            "cutoff_utc": "2026-09-04T16:00:00Z",
                            "current_opponent_key": "MSU",
                            "trust_classification": "UNTRUSTED_SHADOW",
                        }
                    ],
                },
                data_root=root,
            )
            self.assertTrue(any("HASH_MISMATCH" in item for item in mismatch))

    def test_wrong_opponent_and_unresolved_bytes(self) -> None:
        findings = validate_trace_payload(
            {
                "expected_opportunity_ids": ["g1"],
                "current_contest": {
                    "contest_id": "6607349",
                    "home_team_key": "TAMU",
                    "away_team_key": "MSU",
                },
                "traces": [
                    {
                        "raw_source_identity": "ncaa",
                        "raw_sha256": "a" * 64,
                        "canonical_game_id": "g1",
                        "feature_row_identity": "f1",
                        "forecast_row_identity": "p1",
                        "known_at_utc": "2026-09-04T12:00:00Z",
                        "cutoff_utc": "2026-09-04T16:00:00Z",
                        "team_key": "TAMU",
                        "current_opponent_key": "HISTORICAL_FCS",
                        "opponent_key": "HISTORICAL_FCS",
                        "trust_classification": "UNTRUSTED_SHADOW",
                    }
                ],
            }
        )
        self.assertTrue(any("WRONG_OPPONENT" in item for item in findings))
        self.assertTrue(any("RAW_BYTES_UNRESOLVED" in item for item in findings))

    def test_reference_independence_and_saved_pair_tool_has_no_producer_import(
        self,
    ) -> None:
        self.assertEqual([], validate_independence(REPO_ROOT))
        tree = ast.parse(
            (
                REPO_ROOT
                / "tools"
                / "validate_historical_saved_pair_game_grain_successor.py"
            ).read_text(encoding="utf-8")
        )
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertFalse(
            any(
                item == "aggie_analytics.data"
                or item.startswith("aggie_analytics.data.")
                for item in imported
            )
        )


if __name__ == "__main__":
    unittest.main()
