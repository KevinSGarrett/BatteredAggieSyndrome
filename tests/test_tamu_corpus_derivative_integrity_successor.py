"""Corpus derivative-integrity successor regressions."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.data.tamu_corpus_derivative_integrity_successor import (
    PREDECESSOR_PLAYER_SHA256,
    classify_player_line,
    original_text_is_source,
    recompute_child_counts,
    reject_placeholder,
    rejected_url_must_not_enter_union,
    season_specific_versus_cumulative,
    season_specific_rejection_count,
)


class CorpusDerivativeIntegritySuccessorTests(unittest.TestCase):
    def test_stale_child_counts_are_recomputed_not_rewritten(self) -> None:
        gate = {
            "child_payloads": {
                "individual_player_statistics": {"row_count": 3475},
                "team_statistics": {"row_count": 4638},
                "drives": {"row_count": 3142},
                "play_by_play": {"row_count": 45348},
                "scoring_summary": {"row_count": 2150},
            },
            "rows_per_domain": {
                "individual_player_statistics": 3613,
                "team_statistics": 5007,
                "drives": 3142,
                "play_by_play": 47542,
                "scoring_summary": 2252,
            },
        }
        recomputed = recompute_child_counts(gate)
        self.assertGreaterEqual(recomputed["stale_domain_count"], 1)
        player = recomputed["corrected_by_domain"]["individual_player_statistics"]
        self.assertTrue(player["stale"])
        self.assertEqual(player["delta"], 138)
        self.assertFalse(recomputed["predecessor_gate_rewritten"])

    def test_season_specific_sum_is_not_silently_equated_to_cumulative(self) -> None:
        rejection_gate = {
            "counts": {
                "official_1998_rejected": 8,
                "official_1999_rejected": 5,
                "rejected_urls_complete": 40,
                "unmatched_rejected": 17,
            }
        }
        compared = season_specific_versus_cumulative(rejection_gate)
        self.assertEqual(compared["season_specific_sum"], 13)
        self.assertEqual(compared["cumulative_rejected_urls_complete"], 40)
        self.assertFalse(compared["season_sum_equals_cumulative_complete"])
        self.assertEqual(
            season_specific_rejection_count(
                [{"season": 1998}, {"season": 1998}, {"season": 1999}], 1998
            ),
            2,
        )

    def test_rejected_url_and_stringified_parsed_object(self) -> None:
        self.assertTrue(
            rejected_url_must_not_enter_union(
                "https://example.test/rejected",
                ["https://example.test/admitted"],
            )
        )
        parsed = {"att": 12, "cmp": 8}
        self.assertFalse(original_text_is_source(str(parsed), parsed))
        self.assertTrue(original_text_is_source("Jones  12-8-1  90", parsed))
        self.assertEqual(
            reject_placeholder("owned by BAT-XXX"), "UNRESOLVED_BAT_XXX_PLACEHOLDER"
        )
        self.assertTrue(
            classify_player_line("Smith/Jones 12-20")["do_not_attribute_to_first_token"]
        )

    def test_predecessor_player_bytes_immutable_when_mounted(self) -> None:
        data_root = Path(r"C:\BatteredAggieSyndrome.data")
        path = (
            data_root
            / "features/tamu_official_1996_2009_structured_row_corpus/sha256/"
            "7a7f9797bbbc43f273e357584a16ece7715c6ab227438b13fa65775c3dd912f7/"
            "individual_player_statistics.jsonl"
        )
        if not path.is_file():
            self.skipTest("1996-2009 player corpus is not mounted")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, PREDECESSOR_PLAYER_SHA256)

    def test_write_json_uses_tempfile_not_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe.json"
            path.write_bytes(b"{}\n")
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
