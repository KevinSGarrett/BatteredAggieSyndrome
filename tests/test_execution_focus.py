from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import validate_execution_focus


ROOT = Path(__file__).resolve().parents[1]


class ExecutionFocusPolicyTests(unittest.TestCase):
    def test_repository_policy_is_valid_before_new_commit(self) -> None:
        self.assertEqual([], validate_execution_focus.validate(ROOT))

    def test_two_consecutive_process_only_commits_fail(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        with patch.object(
            validate_execution_focus,
            "_git_subjects",
            return_value=["[process] second", "[process] first"],
        ):
            findings = validate_execution_focus._validate_history(ROOT, policy)
        self.assertTrue(any(item.startswith("CONSECUTIVE_PROCESS_ONLY_LIMIT_EXCEEDED") for item in findings))

    def test_material_commit_resets_process_only_streak(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        with patch.object(
            validate_execution_focus,
            "_git_subjects",
            return_value=["[process] newest", "[material] outcome", "[process] oldest"],
        ):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))

    def test_unclassified_commit_fails(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        with patch.object(validate_execution_focus, "_git_subjects", return_value=["ordinary commit"]):
            findings = validate_execution_focus._validate_history(ROOT, policy)
        self.assertTrue(any(item.startswith("COMMIT_CLASSIFICATION_INVALID") for item in findings))

    def test_shallow_ci_validates_reachable_classified_commit(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        with (
            patch.object(
                validate_execution_focus,
                "_git_subjects",
                side_effect=[RuntimeError("baseline unavailable"), ["[process] adoption"]],
            ),
            patch.object(validate_execution_focus, "_git_is_shallow", return_value=True),
        ):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))

    def test_shallow_ci_ignores_only_exact_github_synthetic_merge(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        synthetic = "Merge " + "a" * 40 + " into " + "b" * 40
        with (
            patch.object(
                validate_execution_focus,
                "_git_subjects",
                side_effect=[RuntimeError("baseline unavailable"), [synthetic]],
            ),
            patch.object(validate_execution_focus, "_git_is_shallow", return_value=True),
        ):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))

    def test_pull_request_event_ignores_exact_github_synthetic_merge(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        synthetic = "Merge " + "a" * 40 + " into " + "b" * 40
        with (
            patch.object(validate_execution_focus, "_git_subjects", return_value=[synthetic]),
            patch.dict("os.environ", {"GITHUB_EVENT_NAME": "pull_request"}, clear=False),
        ):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))


if __name__ == "__main__":
    unittest.main()
