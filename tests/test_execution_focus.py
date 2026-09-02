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
            "_git_commits",
            return_value=[("b" * 40, "[process] second"), ("a" * 40, "[process] first")],
        ), patch.object(validate_execution_focus, "_git_commit_changed_paths", return_value=["jira/README.md"]):
            findings = validate_execution_focus._validate_history(ROOT, policy)
        self.assertTrue(any(item.startswith("CONSECUTIVE_PROCESS_ONLY_LIMIT_EXCEEDED") for item in findings))

    def test_material_commit_resets_process_only_streak(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        with patch.object(
            validate_execution_focus,
            "_git_commits",
            return_value=[
                ("c" * 40, "[process] newest"),
                ("b" * 40, "[material] outcome"),
                ("a" * 40, "[process] oldest"),
            ],
        ), patch.object(validate_execution_focus, "_git_commit_changed_paths", return_value=["jira/README.md"]):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))

    def test_unclassified_commit_fails(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        with patch.object(
            validate_execution_focus,
            "_git_commits",
            return_value=[("a" * 40, "ordinary commit")],
        ), patch.object(validate_execution_focus, "_git_commit_changed_paths", return_value=["docs/notes.md"]):
            findings = validate_execution_focus._validate_history(ROOT, policy)
        self.assertTrue(any(item.startswith("COMMIT_CLASSIFICATION_INVALID") for item in findings))

    def test_shallow_ci_validates_reachable_classified_commit(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        with (
            patch.object(
                validate_execution_focus,
                "_git_commits",
                side_effect=[RuntimeError("baseline unavailable"), [("a" * 40, "[process] adoption")]],
            ),
            patch.object(validate_execution_focus, "_git_is_shallow", return_value=True),
            patch.object(validate_execution_focus, "_git_commit_changed_paths", return_value=["jira/README.md"]),
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
                "_git_commits",
                side_effect=[RuntimeError("baseline unavailable"), [("a" * 40, synthetic)]],
            ),
            patch.object(validate_execution_focus, "_git_is_shallow", return_value=True),
            patch.object(validate_execution_focus, "_git_commit_changed_paths", return_value=["jira/README.md"]),
        ):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))

    def test_pull_request_event_ignores_exact_github_synthetic_merge(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        synthetic = "Merge " + "a" * 40 + " into " + "b" * 40
        with (
            patch.object(
                validate_execution_focus,
                "_git_commits",
                return_value=[("a" * 40, synthetic)],
            ),
            patch.dict("os.environ", {"GITHUB_EVENT_NAME": "pull_request"}, clear=False),
            patch.object(validate_execution_focus, "_git_commit_changed_paths", return_value=["jira/README.md"]),
        ):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))

    def test_exact_historical_integration_correction_is_sha_scoped(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        correction = policy["commit_classification"]["historical_integration_corrections"][0]
        with patch.object(
            validate_execution_focus,
            "_git_commits",
            return_value=[(correction["commit_sha"], "unclassified squash subject")],
        ), patch.object(validate_execution_focus, "_git_commit_changed_paths", return_value=["jira/README.md"]):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))
        with patch.object(
            validate_execution_focus,
            "_git_commits",
            return_value=[("f" * 40, "unclassified squash subject")],
        ), patch.object(validate_execution_focus, "_git_commit_changed_paths", return_value=["jira/README.md"]):
            findings = validate_execution_focus._validate_history(ROOT, policy)
        self.assertTrue(any(item.startswith("COMMIT_CLASSIFICATION_INVALID") for item in findings))

    def test_historical_correction_overrides_wrong_process_marker(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        fake_sha = "b" * 40
        policy["commit_classification"]["historical_integration_corrections"].append(
            {
                "commit_sha": fake_sha,
                "head_sha": fake_sha,
                "pull_request": 671,
                "classification": "[material]",
                "reason": "unit-test override",
            }
        )
        with patch.object(
            validate_execution_focus,
            "_git_commits",
            return_value=[(fake_sha, "[process] merge that touched material paths")],
        ), patch.object(
            validate_execution_focus,
            "_git_commit_changed_paths",
            return_value=["src/aggie_analytics/data/example.py"],
        ):
            self.assertEqual([], validate_execution_focus._validate_history(ROOT, policy))

    def test_process_commit_touching_material_paths_fails(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/execution_focus_policy.json").read_text(encoding="utf-8")
        )
        with patch.object(
            validate_execution_focus,
            "_git_commits",
            return_value=[("a" * 40, "[process] incorrect classification")],
        ), patch.object(
            validate_execution_focus,
            "_git_commit_changed_paths",
            return_value=["src/aggie_analytics/data/example.py"],
        ), patch.object(
            validate_execution_focus,
            "_git_commits_unique_to_head",
            return_value={"a" * 40},
        ), patch.dict("os.environ", {"AGGIE_ANALYTICS_ENFORCE_PATH_CLASSIFICATION": "1"}, clear=False):
            findings = validate_execution_focus._validate_history(ROOT, policy)
        self.assertTrue(any(item.startswith("PROCESS_COMMIT_TOUCHES_MATERIAL_PATHS") for item in findings))


if __name__ == "__main__":
    unittest.main()
