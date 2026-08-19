from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_rich_structure import (  # noqa: E402
    RICH_STRUCTURE_DOMAINS,
    RichStructureViolation,
    classify_games,
    is_rich_structured,
    scoring_summary_present,
    validate_acquisition_gate,
    validate_rich_structure_artifacts,
    validate_union_gate,
)


def _coverage(**flags: str) -> dict[str, str]:
    return {
        "team_statistics": "ABSENT",
        "individual_player_statistics": "ABSENT",
        "play_by_play": "ABSENT",
        "scoring_summary": "ABSENT",
        **flags,
    }


def _game(**flags: str) -> dict[str, object]:
    return {"url": "https://example.test/box", "domain_coverage": _coverage(**flags)}


def _acquisition_gate(*, rich: int, metadata: int, scoring: int, team: int = 0, player: int = 0, pbp: int = 0) -> dict:
    return {
        "counts": {
            "normalized_games": rich + metadata,
            "rich_structured_games": rich,
            "metadata_only_games": metadata,
            "scoring_summary_present_games": scoring,
        },
        "domain_coverage": {
            "team_statistics": {"present_games": team, "absent_games": rich + metadata - team},
            "individual_player_statistics": {"present_games": player, "absent_games": rich + metadata - player},
            "play_by_play": {"present_games": pbp, "absent_games": rich + metadata - pbp},
            "scoring_summary": {"present_games": scoring, "absent_games": rich + metadata - scoring},
        },
    }


class RichStructureDefinitionTests(unittest.TestCase):
    def test_scoring_summary_alone_is_metadata_only(self) -> None:
        game = _game(scoring_summary="PRESENT")
        self.assertTrue(scoring_summary_present(game))
        self.assertFalse(is_rich_structured(game))
        self.assertEqual(
            classify_games([game]),
            {
                "rich_structured_games": 0,
                "metadata_only_games": 1,
                "scoring_summary_present_games": 1,
                "game_count": 1,
            },
        )

    def test_each_canonical_domain_makes_a_game_rich(self) -> None:
        for domain in RICH_STRUCTURE_DOMAINS:
            with self.subTest(domain=domain):
                self.assertTrue(is_rich_structured(_game(**{domain: "PRESENT"})))

    def test_cycle10_scoring_only_cohort_is_zero_rich(self) -> None:
        games = [_game(scoring_summary="PRESENT") for _ in range(25)]
        classified = classify_games(games)
        self.assertEqual(classified["rich_structured_games"], 0)
        self.assertEqual(classified["metadata_only_games"], 25)
        self.assertEqual(classified["scoring_summary_present_games"], 25)


class AcquisitionGateConsistencyTests(unittest.TestCase):
    def test_current_bat586_scoring_as_rich_fails(self) -> None:
        findings = validate_acquisition_gate(
            Path("pre2010.json"),
            _acquisition_gate(rich=25, metadata=0, scoring=25, team=0, player=0, pbp=0),
        )
        self.assertTrue(any("scoring-summary presence alone" in item for item in findings))

    def test_corrected_bat586_counts_pass(self) -> None:
        findings = validate_acquisition_gate(
            Path("pre2010.json"),
            _acquisition_gate(rich=0, metadata=25, scoring=25, team=0, player=0, pbp=0),
        )
        self.assertEqual(findings, [])

    def test_missing_scoring_summary_count_fails(self) -> None:
        gate = _acquisition_gate(rich=0, metadata=25, scoring=25)
        del gate["counts"]["scoring_summary_present_games"]
        findings = validate_acquisition_gate(Path("pre2010.json"), gate)
        self.assertTrue(any("scoring_summary_present_games" in item for item in findings))

    def test_extra_rich_count_without_domains_fails(self) -> None:
        findings = validate_acquisition_gate(
            Path("pre2010.json"),
            _acquisition_gate(rich=13, metadata=0, scoring=13, team=0, player=0, pbp=0),
        )
        self.assertTrue(findings)


class UnionGateConsistencyTests(unittest.TestCase):
    def test_union_rejects_scoring_only_as_rich(self) -> None:
        findings = validate_union_gate(
            Path("union.json"),
            {
                "admitted_pre2010_games": [_game(scoring_summary="PRESENT")],
                "coverage_by_season": {"2008": {"rich_structured_games": 1, "metadata_only_games": 0}},
            },
        )
        self.assertTrue(findings)

    def test_union_accepts_metadata_only_scoring_summary(self) -> None:
        findings = validate_union_gate(
            Path("union.json"),
            {
                "admitted_pre2010_games": [_game(scoring_summary="PRESENT")],
                "coverage_by_season": {"2008": {"rich_structured_games": 0, "metadata_only_games": 1}},
            },
        )
        self.assertEqual(findings, [])

    def test_union_and_acquisition_definitions_must_agree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            lake = root / "artifacts" / "data_lake"
            lake.mkdir(parents=True)
            (lake / "tamu_official_pre2010_boxscore_gate.json").write_text(
                json.dumps(_acquisition_gate(rich=25, metadata=0, scoring=25)),
                encoding="utf-8",
            )
            (lake / "tamu_official_gamebook_union_expanded_gate.json").write_text(
                json.dumps(
                    {
                        "admitted_pre2010_games": [_game(scoring_summary="PRESENT") for _ in range(25)],
                        "coverage_by_season": {
                            "2009": {"rich_structured_games": 0, "metadata_only_games": 13},
                            "2008": {"rich_structured_games": 0, "metadata_only_games": 12},
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RichStructureViolation):
                validate_rich_structure_artifacts(repo_root=root)


class CommittedArtifactTests(unittest.TestCase):
    def test_committed_official_artifacts_use_one_definition(self) -> None:
        result = validate_rich_structure_artifacts(repo_root=REPO_ROOT)
        self.assertEqual(result["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
