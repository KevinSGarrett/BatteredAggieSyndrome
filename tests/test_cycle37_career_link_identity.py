"""Cycle #37 - Attempt #2 - ACTUAL_STATE: W37R-65, a career row's own link refuses a display it contradicts."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cycle37" / "r37_05_career_reparse.py"

ROWS = [
    {"id": 193, "school": "Miami (OH)", "mascot": "RedHawks", "classification": "fbs"},
    {"id": 2390, "school": "Miami", "mascot": "Hurricanes", "classification": "fbs"},
    {"id": 163, "school": "Princeton", "mascot": "Tigers", "classification": "fcs"},
    {"id": 2731, "school": "Williams", "mascot": "Ephs", "classification": "iii"},
    {"id": 2674, "school": "Valparaiso", "mascot": "Beacons", "classification": "fcs"},
    {"id": 2370, "school": "Mary Hardin-Baylor", "mascot": "Crusaders", "classification": "iii"},
]


def _resolver():
    spec = importlib.util.spec_from_file_location("r37_05_career_reparse", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_payloads = lambda *args, **kwargs: {2000: ("synthetic", ROWS)}
    module.read_jsonl = lambda path: []
    return module.Resolver()


class LinkIdentityTests(unittest.TestCase):
    """The link's declared identity only ever refuses a resolution; it never makes one."""

    def test_unqualified_school_and_mascot_contradicts_the_display(self) -> None:
        chosen = _resolver().resolve("Miami", "Miami RedHawks football")
        self.assertEqual(chosen["state"], "CONFLICT_DISPLAY_AND_LINK_RESOLVE_TO_DIFFERENT_PROGRAMS")
        self.assertIsNone(chosen["program_id"])
        self.assertEqual(chosen["candidates"], ["SRC-002:TEAM:193", "SRC-002:TEAM:2390"])
        self.assertEqual(chosen["link_basis"], "LINK_TARGET_IS_A_DECLARED_SCHOOL_WITHOUT_ITS_QUALIFIER_PLUS_ITS_MASCOT")

    def test_a_link_to_a_program_outside_the_population_still_contradicts(self) -> None:
        chosen = _resolver().resolve("Princeton", "Williams Ephs football")
        self.assertEqual(chosen["state"], "CONFLICT_DISPLAY_AND_LINK_RESOLVE_TO_DIFFERENT_PROGRAMS")
        self.assertEqual(chosen["link_basis"], "LINK_TARGET_IS_A_DECLARED_SCHOOL_PLUS_MASCOT_SPELLING")

    def test_a_historical_mascot_of_the_same_school_is_not_a_conflict(self) -> None:
        # "Crusaders" is another program's declared mascot, but not with Valparaiso's school name
        chosen = _resolver().resolve("Valparaiso", "Valparaiso Crusaders football")
        self.assertEqual(chosen["state"], "RESOLVED_SINGLE_CANONICAL_PROGRAM")
        self.assertEqual(chosen["program_id"], "SRC-002:TEAM:2674")

    def test_an_agreeing_link_keeps_the_display_resolution(self) -> None:
        chosen = _resolver().resolve("Miami (OH)", "Miami RedHawks football")
        self.assertEqual(chosen["program_id"], "SRC-002:TEAM:193")

    def test_the_identity_never_resolves_an_unresolved_display(self) -> None:
        chosen = _resolver().resolve("Some Other College", "Miami RedHawks football")
        self.assertIsNone(chosen["program_id"])
        self.assertNotIn("link_basis", chosen)


if __name__ == "__main__":
    unittest.main()
