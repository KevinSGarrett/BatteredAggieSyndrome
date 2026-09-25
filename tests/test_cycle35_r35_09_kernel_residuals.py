"""R35-09 (Cycle #35 closeout review, 20260921T025300Z), section 7:
"Finish actual kernel reconstruction and the other executable R35
obligations; receipt generation is not a substitute. Maintain zero proven PIT
or zero eligible forecasts where justified."

The reconstruction ran, but two residuals were left as aggregate counts --
15 rows whose stored prior count the reference could not justify, and 796
rows whose game was not in the declared sources. A count is not a
disposition. Each row is now inventoried in full and given a disposition
derived from what the declared sources actually cover.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_09_independent_kernel_reference import residual_disposition  # noqa: E402

ARTIFACT = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
    / "20260921T025300Z_closeout"
    / "R35_09_INDEPENDENT_KERNEL_REFERENCE.json"
)


def games(*seasons: int) -> dict[str, dict]:
    return {f"g{year}": {"season": year} for year in seasons}


class ResidualDispositionTests(unittest.TestCase):
    def test_a_row_whose_season_was_never_acquired_is_named_as_such(self) -> None:
        comparison = {
            "absent_game_rows": [{"canonical_game_id": "gX", "season": 2025}],
            "unjustified_rows": [],
        }
        out = residual_disposition(comparison, games(2023, 2026))
        self.assertEqual(
            out["absent_game_rows_by_disposition"], {"SEASON_NOT_ACQUIRED_AT_ALL": 1}
        )

    def test_a_row_whose_season_was_acquired_is_a_gap_in_the_pull_not_the_range(
        self,
    ) -> None:
        """"We never pulled 2025" and "we pulled 2023 but missed this game"
        are different acquisition failures and get different fixes."""
        comparison = {
            "absent_game_rows": [{"canonical_game_id": "gX", "season": 2023}],
            "unjustified_rows": [],
        }
        out = residual_disposition(comparison, games(2023, 2026))
        self.assertEqual(
            out["absent_game_rows_by_disposition"],
            {"SEASON_ACQUIRED_BUT_THIS_GAME_IS_NOT_IN_THE_PULL": 1},
        )

    def test_an_excess_prior_count_is_explained_by_a_missing_prior_season(self) -> None:
        comparison = {
            "absent_game_rows": [],
            "unjustified_rows": [{"season": 2026, "excess_priors": 8}],
        }
        out = residual_disposition(comparison, games(2023, 2026))
        self.assertEqual(
            out["unjustified_rows_by_disposition"],
            {"EXPLAINED_BY_UNACQUIRED_PRIOR_SEASONS": 1},
        )
        self.assertEqual(
            comparison["unjustified_rows"][0][
                "seasons_missing_from_declared_sources_before_this_row"
            ],
            [2024, 2025],
        )

    def test_an_excess_with_no_missing_season_stays_unexplained(self) -> None:
        """With every prior season acquired there is nothing to attribute the
        excess to, and it must not be absorbed into the same bucket."""
        comparison = {
            "absent_game_rows": [],
            "unjustified_rows": [{"season": 2024, "excess_priors": 3}],
        }
        out = residual_disposition(comparison, games(2022, 2023, 2024))
        self.assertEqual(
            out["unjustified_rows_by_disposition"],
            {
                "UNEXPLAINED_PRODUCER_COUNTED_PRIORS_THE_RAW_DATA_DOES_NOT_SUPPLY": 1
            },
        )

    def test_every_residual_row_gets_a_disposition(self) -> None:
        comparison = {
            "absent_game_rows": [
                {"canonical_game_id": f"g{n}", "season": 2023 + (n % 3)}
                for n in range(9)
            ],
            "unjustified_rows": [{"season": 2026} for _ in range(4)],
        }
        out = residual_disposition(comparison, games(2023, 2026))
        self.assertTrue(out["every_residual_has_a_disposition"])
        self.assertEqual(sum(out["absent_game_rows_by_disposition"].values()), 9)
        self.assertEqual(sum(out["unjustified_rows_by_disposition"].values()), 4)

    def test_the_missing_season_range_is_computed_not_declared(self) -> None:
        out = residual_disposition(
            {"absent_game_rows": [], "unjustified_rows": []},
            games(2020, 2021, 2024),
        )
        self.assertEqual(out["seasons_missing_from_declared_sources"], [2022, 2023])


class RealKernelResidualTests(unittest.TestCase):
    def setUp(self) -> None:
        if not ARTIFACT.is_file():
            self.skipTest("the kernel reference has not been re-run")
        self.comparison = json.loads(ARTIFACT.read_text(encoding="utf-8"))["comparison"]

    def test_the_residuals_are_inventoried_in_full_not_sampled(self) -> None:
        self.assertTrue(self.comparison["residuals_are_inventoried_in_full"])
        self.assertEqual(
            len(self.comparison["unjustified_rows"]),
            self.comparison["unjustified_row_count"],
        )
        self.assertEqual(
            len(self.comparison["absent_game_rows"]),
            self.comparison["row_states"]["GAME_NOT_IN_DECLARED_RAW_SOURCES"],
        )

    def test_no_residual_is_left_without_a_disposition(self) -> None:
        self.assertTrue(
            self.comparison["residual_disposition"]["every_residual_has_a_disposition"]
        )

    def test_no_stored_row_counts_priors_that_stay_unexplained(self) -> None:
        by_disposition = self.comparison["residual_disposition"][
            "unjustified_rows_by_disposition"
        ]
        self.assertNotIn(
            "UNEXPLAINED_PRODUCER_COUNTED_PRIORS_THE_RAW_DATA_DOES_NOT_SUPPLY",
            by_disposition,
        )

    def test_the_target_exclusion_invariant_still_holds(self) -> None:
        """No row may draw on its own contest or anything later."""
        self.assertEqual(self.comparison["target_exclusion_violation_count"], 0)
        self.assertEqual(self.comparison["game_pair_incoherence_count"], 0)

    def test_zero_independent_pit_proofs_is_maintained(self) -> None:
        authority = json.loads(ARTIFACT.read_text(encoding="utf-8"))[
            "producer_authority_labels"
        ]
        self.assertEqual(authority["independent_pit_proof_count"], 0)


if __name__ == "__main__":
    unittest.main()
