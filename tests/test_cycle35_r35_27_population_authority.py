"""R35-27 (Cycle #35 continuation, 20260921T055921Z), section 3.

"Derive year membership from its bound authority, not the current clock or a
guessed default... If membership itself is unproven, record that population
uncertainty explicitly; do not omit the year and present the narrower
denominator as national completion."

The danger here is re-introducing the fabrication MF35-05 removed. That
repair stopped the builder dating a seasonless row to the current year. The
distinction these tests pin down is that a season may be bound from the
DECLARED REQUEST that produced a file, proved by content, and from nothing
else -- never from the clock, never from a single covering guess.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_27_national_population_authority import (  # noqa: E402
    AUTHORITY_NONE,
    AUTHORITY_PER_ROW,
    AUTHORITY_RECEIPT,
    LINKAGE_ABSENT,
    LINKAGE_AMBIGUOUS,
    LINKAGE_PROVED,
    cached_team_payloads,
    prove_receipt_linkage,
    resolve_membership_file,
)

REAL_ARTIFACT = (
    Path("C:/BatteredAggieSyndrome.data/ops/cycle35/runs")
    / "20260921T055921Z_implementation"
    / "CYCLE35_NATIONAL_POPULATION_AUTHORITY.json"
)


def payload(year: int, ids: list[str], digest: str = "") -> dict:
    return {
        "year": year,
        "receipt_sha256": digest or f"sha{year}",
        "cached_payload": f"raw/teams/{year}.json",
        "payload_rows": len(ids),
        "program_ids": set(ids),
        "retrieved_at_utc": "2026-09-09T18:08:44Z",
        "status": "CACHE_HIT",
    }


def write_membership(root: Path, name: str, rows: list[dict]) -> Path:
    path = root / name
    path.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    return path


class LinkageProofTests(unittest.TestCase):
    def test_exactly_one_covering_year_is_proved(self) -> None:
        payloads = {
            2023: payload(2023, ["1", "2"]),
            2026: payload(2026, ["1", "2", "3"]),
        }
        proof = prove_receipt_linkage({"1", "2", "3"}, payloads)
        self.assertEqual(proof["state"], LINKAGE_PROVED)
        self.assertEqual(proof["bound_year"], 2026)

    def test_two_covering_years_bind_nothing(self) -> None:
        """An ambiguous linkage is not a 50/50 guess to be resolved by
        picking the later year. It binds nothing."""
        payloads = {
            2025: payload(2025, ["1", "2", "3"]),
            2026: payload(2026, ["1", "2", "3"]),
        }
        proof = prove_receipt_linkage({"1", "2"}, payloads)
        self.assertEqual(proof["state"], LINKAGE_AMBIGUOUS)
        self.assertIsNone(proof["bound_year"])

    def test_no_covering_year_binds_nothing(self) -> None:
        payloads = {2026: payload(2026, ["1", "2"])}
        proof = prove_receipt_linkage({"1", "2", "999"}, payloads)
        self.assertEqual(proof["state"], LINKAGE_ABSENT)
        self.assertIsNone(proof["bound_year"])

    def test_a_near_miss_does_not_count_as_covering(self) -> None:
        """Covering 265 of 266 is not covering. The real 2013 payload misses
        five current programs and must not be accepted as the source."""
        payloads = {2013: payload(2013, [str(n) for n in range(265)])}
        proof = prove_receipt_linkage({str(n) for n in range(266)}, payloads)
        self.assertEqual(proof["state"], LINKAGE_ABSENT)

    def test_an_empty_program_set_is_never_covered(self) -> None:
        payloads = {2026: payload(2026, ["1"])}
        self.assertEqual(prove_receipt_linkage(set(), payloads)["state"], LINKAGE_ABSENT)


class MembershipResolutionTests(unittest.TestCase):
    def test_per_row_seasons_need_no_receipt(self) -> None:
        with TemporaryDirectory() as tmp:
            path = write_membership(
                Path(tmp),
                "HIST.jsonl",
                [
                    {"program_id": "SRC-002:TEAM:1", "season": 1999},
                    {"program_id": "SRC-002:TEAM:2", "season": 2000},
                ],
            )
            record = resolve_membership_file(path, {})
        self.assertEqual(record["authority"], AUTHORITY_PER_ROW)
        self.assertEqual(record["seasons"], [1999, 2000])

    def test_a_seasonless_file_binds_to_its_proved_receipt_year(self) -> None:
        with TemporaryDirectory() as tmp:
            path = write_membership(
                Path(tmp),
                "CURRENT.jsonl",
                [{"program_id": "SRC-002:TEAM:1"}, {"program_id": "SRC-002:TEAM:2"}],
            )
            record = resolve_membership_file(
                path, {2026: payload(2026, ["1", "2"]), 2023: payload(2023, ["1"])}
            )
        self.assertEqual(record["authority"], AUTHORITY_RECEIPT)
        self.assertEqual(record["seasons"], [2026])
        self.assertIn("not the wall clock", record["detail"])

    def test_a_seasonless_file_with_no_receipts_binds_nothing(self) -> None:
        """This is the MF35-05 fabrication. With no receipt to prove a year,
        the file stays unbound even though the current year is 2026."""
        with TemporaryDirectory() as tmp:
            path = write_membership(
                Path(tmp), "CURRENT.jsonl", [{"program_id": "SRC-002:TEAM:1"}]
            )
            record = resolve_membership_file(path, {})
        self.assertEqual(record["authority"], AUTHORITY_NONE)
        self.assertEqual(record["seasons"], [])

    def test_a_partially_seasoned_file_is_not_bound_as_a_whole(self) -> None:
        """A row must not be dated from its neighbours."""
        with TemporaryDirectory() as tmp:
            path = write_membership(
                Path(tmp),
                "MIXED.jsonl",
                [
                    {"program_id": "SRC-002:TEAM:1", "season": 2020},
                    {"program_id": "SRC-002:TEAM:2"},
                ],
            )
            record = resolve_membership_file(path, {2026: payload(2026, ["1", "2"])})
        self.assertEqual(record["authority"], AUTHORITY_NONE)
        self.assertIn("no row is dated from its neighbours", record["detail"])


class ScopeUncertaintyTests(unittest.TestCase):
    def build_scope(self, tmp: Path, rows: list[dict], payloads: dict):
        path = write_membership(tmp, "M.jsonl", rows)
        import r35_27_national_population_authority as module

        original = module.cached_team_payloads
        module.cached_team_payloads = lambda *a, **k: payloads
        try:
            return module.build(
                membership_files=(path,), scope=(2024, 2026)
            )
        finally:
            module.cached_team_payloads = original

    def test_an_unbound_season_is_reported_not_omitted(self) -> None:
        with TemporaryDirectory() as tmp:
            result = self.build_scope(
                Path(tmp),
                [{"program_id": "SRC-002:TEAM:1"}],
                {2026: payload(2026, ["1"])},
            )
        self.assertEqual(result["seasons_without_membership_authority"], [2024, 2025])
        reasons = {u["season"]: u["reason"] for u in result["population_uncertainty"]}
        self.assertEqual(reasons[2024], "DECLARED_YEAR_NOT_ACQUIRED")
        self.assertEqual(reasons[2025], "DECLARED_YEAR_NOT_ACQUIRED")
        self.assertFalse(result["scope_is_fully_bound"])

    def test_an_acquired_but_unmaterialised_season_reads_differently(self) -> None:
        """A season we never requested and one we requested but never turned
        into a membership file need different fixes, so they get different
        reasons."""
        with TemporaryDirectory() as tmp:
            result = self.build_scope(
                Path(tmp),
                [{"program_id": "SRC-002:TEAM:1"}],
                {2026: payload(2026, ["1"]), 2025: payload(2025, ["9"])},
            )
        reasons = {u["season"]: u["reason"] for u in result["population_uncertainty"]}
        self.assertEqual(
            reasons[2025], "ACQUIRED_BUT_NOT_MATERIALISED_INTO_A_MEMBERSHIP_FILE"
        )
        self.assertEqual(reasons[2024], "DECLARED_YEAR_NOT_ACQUIRED")

    def test_a_fully_bound_scope_says_so(self) -> None:
        with TemporaryDirectory() as tmp:
            result = self.build_scope(
                Path(tmp),
                [
                    {"program_id": "SRC-002:TEAM:1", "season": 2024},
                    {"program_id": "SRC-002:TEAM:1", "season": 2025},
                    {"program_id": "SRC-002:TEAM:1", "season": 2026},
                ],
                {},
            )
        self.assertTrue(result["scope_is_fully_bound"])
        self.assertEqual(result["population_uncertainty"], [])


class RealCycleTests(unittest.TestCase):
    def test_the_real_teams_receipts_bind_to_cached_files(self) -> None:
        payloads = cached_team_payloads()
        if not payloads:
            self.skipTest("the cycle30 acquisition cache is not mounted")
        self.assertIn(2026, payloads)
        self.assertNotIn(2024, payloads)
        self.assertNotIn(2025, payloads)
        self.assertEqual(payloads[2026]["status"], "CACHE_HIT")

    def test_the_real_current_file_binds_to_2026_and_only_2026(self) -> None:
        payloads = cached_team_payloads()
        if not payloads:
            self.skipTest("the cycle30 acquisition cache is not mounted")
        current = (
            Path("C:/BatteredAggieSyndrome.data/ops/cycle30_work/outputs")
            / "CURRENT_2026_PROGRAMS.jsonl"
        )
        if not current.is_file():
            self.skipTest("the current membership file is not mounted")
        record = resolve_membership_file(current, payloads)
        self.assertEqual(record["authority"], AUTHORITY_RECEIPT)
        self.assertEqual(record["seasons"], [2026])
        covering = [
            row
            for row in record["receipt_linkage"]["coverage_by_declared_year"]
            if row["covers_all"]
        ]
        self.assertEqual([row["year"] for row in covering], [2026])

    def test_the_real_scope_reports_2024_and_2025_as_uncertainty(self) -> None:
        if not REAL_ARTIFACT.is_file():
            self.skipTest("the population authority artifact has not been generated")
        result = json.loads(REAL_ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(result["seasons_without_membership_authority"], [2024, 2025])
        self.assertFalse(result["scope_is_fully_bound"])
        self.assertEqual(len(result["seasons_with_membership_authority"]), 62)


if __name__ == "__main__":
    unittest.main()
