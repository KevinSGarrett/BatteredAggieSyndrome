from __future__ import annotations

import unittest

from tools.queue_openai_gamebook_candidate_work import _select_route


class OpenAIGamebookCandidateRouteSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "routes": [
                {
                    "model": "gpt-5.6-luna",
                    "reasoning_effort": "none",
                    "case_ids": ["SHARED_CASE", "LUNA_ONLY"],
                },
                {
                    "model": "gpt-5.6-terra",
                    "reasoning_effort": "low",
                    "case_ids": ["SHARED_CASE"],
                },
            ]
        }

    def test_selects_explicit_comparative_model_route(self) -> None:
        route = _select_route(self.config, "SHARED_CASE", "gpt-5.6-terra")
        self.assertEqual("gpt-5.6-terra", route["model"])
        self.assertEqual("low", route["reasoning_effort"])

    def test_requires_model_for_ambiguous_comparative_case(self) -> None:
        with self.assertRaisesRegex(SystemExit, "--model is required"):
            _select_route(self.config, "SHARED_CASE", None)

    def test_preserves_single_route_default(self) -> None:
        route = _select_route(self.config, "LUNA_ONLY", None)
        self.assertEqual("gpt-5.6-luna", route["model"])

    def test_rejects_unknown_model_for_case(self) -> None:
        with self.assertRaisesRegex(SystemExit, "resolve exactly once"):
            _select_route(self.config, "SHARED_CASE", "gpt-5.6-sol")

    def test_rejects_duplicate_exact_route_identity(self) -> None:
        duplicate = {"routes": [self.config["routes"][0], dict(self.config["routes"][0])]}
        with self.assertRaisesRegex(SystemExit, "resolve exactly once"):
            _select_route(duplicate, "LUNA_ONLY", "gpt-5.6-luna")


if __name__ == "__main__":
    unittest.main()
