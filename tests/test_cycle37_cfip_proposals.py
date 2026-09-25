"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-13-AC08: the CFIP proposal tool must bind every proposal to exact owner
sections, produce the same marker for the same evidence, refuse to claim a
fixture it does not have, and find an existing effect before it posts.
Nothing here touches the network.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "cycle37"
sys.path.insert(0, str(TOOLS))
_spec = importlib.util.spec_from_file_location("r37_13_cfip_proposals", TOOLS / "r37_13_cfip_proposals.py")
proposals_tool = importlib.util.module_from_spec(_spec)
sys.modules["r37_13_cfip_proposals"] = proposals_tool
_spec.loader.exec_module(proposals_tool)

NEGATIVES = ["negative_empty_projection", "negative_mixed_cutoffs", "negative_empty_evidence",
             "negative_blank_evidence_string", "negative_one_of_two_without_evidence",
             "negative_known_at_after_cutoff", "negative_two_programs"]


def composition(negatives=NEGATIVES):
    fixtures = [{"fixture": "positive_single_head_coach"}] + [{"fixture": n} for n in negatives]
    return {
        "vector": {"producer": "p", "wheel_version": "0.1.2", "wheel_sha256": "a" * 64,
                   "consumer": "c", "schema": "context/StaffSnapshotV1", "ruleset_id": "r",
                   "predecessor_producer": "q"},
        "lossless_envelope": {"lost_by_projection": ["roles", "rights"]},
        "fixtures": fixtures, "positives": 1, "positives_accepted_by_both": 1,
        "negatives": len(negatives), "negatives_caught_by_bas_adapter": len(negatives),
        "negatives_caught_only_by_released_wheel": [],
        "source_scheme_vs_f10_state": ["intelligence/TeamSchemeSnapshotV1"],
    }


def sections():
    out = {}
    for pairs in proposals_tool.BINDINGS.values():
        for owner_path, heading in pairs:
            out[(owner_path, heading)] = {"section_sha256": f"sha-{owner_path}-{heading}"}
    return out


COUNTS = {"scheme_assertion": 10, "responsibility_assertion": 5}


class ProposalTests(unittest.TestCase):
    def test_every_proposal_names_every_bound_section_digest(self) -> None:
        built = proposals_tool.build_proposals(composition(), sections(), COUNTS)
        self.assertEqual(sorted(built), ["CFIP-19", "CFIP-22", "CFIP-24", "CFIP-27"])
        for issue, proposal in built.items():
            for owner_path, heading in proposals_tool.BINDINGS[issue]:
                with self.subTest(issue=issue, heading=heading):
                    self.assertIn(f"sha-{owner_path}-{heading}", proposal["text"])
            self.assertIn("not adoption", proposal["text"])
            self.assertTrue(proposal["text"].endswith(proposal["marker"]))

    def test_the_marker_is_deterministic_and_content_bound(self) -> None:
        first = proposals_tool.build_proposals(composition(), sections(), COUNTS)
        second = proposals_tool.build_proposals(composition(), sections(), COUNTS)
        self.assertEqual({k: v["marker"] for k, v in first.items()},
                         {k: v["marker"] for k, v in second.items()})
        changed = proposals_tool.build_proposals(composition(), sections(),
                                                 {"scheme_assertion": 11, "responsibility_assertion": 5})
        self.assertNotEqual(first["CFIP-22"]["marker"], changed["CFIP-22"]["marker"])

    def test_a_missing_owner_section_is_refused(self) -> None:
        partial = sections()
        partial.pop(next(iter(partial)))
        with self.assertRaises(SystemExit):
            proposals_tool.build_proposals(composition(), partial, COUNTS)

    def test_a_claimed_fixture_that_does_not_exist_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            proposals_tool.build_proposals(composition(NEGATIVES[1:]), sections(), COUNTS)

    def test_the_unexercised_roster_case_is_stated_not_hidden(self) -> None:
        text = proposals_tool.build_proposals(composition(), sections(), COUNTS)["CFIP-27"]["text"]
        self.assertIn("Wrong-season roster - NOT covered", text)


class EffectTests(unittest.TestCase):
    def test_an_existing_marker_is_an_existing_effect(self) -> None:
        comments = [{"id": "1", "body": "unrelated"},
                    {"id": "2", "body": "text\n\n[BAS-C37A2-R37-13-AC08 CFIP-22 0123456789abcdef]"}]
        self.assertEqual(proposals_tool.existing_effect(comments, "CFIP-22")["id"], "2")
        self.assertIsNone(proposals_tool.existing_effect(comments, "CFIP-19"))

    def test_a_different_issue_marker_is_not_an_effect_here(self) -> None:
        comments = [{"id": "3", "body": "[BAS-C37A2-R37-13-AC08 CFIP-19 0123456789abcdef]"}]
        self.assertIsNone(proposals_tool.existing_effect(comments, "CFIP-27"))

    def test_the_client_cannot_transition_edit_or_delete(self) -> None:
        for name in ("put", "delete", "transition", "edit", "create_issue", "update"):
            self.assertFalse(hasattr(proposals_tool.OwnerCommentClient, name), name)

    def test_readback_comparison_ignores_line_endings_and_trailing_space(self) -> None:
        self.assertEqual(proposals_tool.normalise("a \r\nb\r\n"), proposals_tool.normalise("a\nb"))


if __name__ == "__main__":
    unittest.main()
