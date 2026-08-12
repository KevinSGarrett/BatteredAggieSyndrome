from __future__ import annotations

from dataclasses import dataclass

from .orchestration import validate_cursor_request


@dataclass(frozen=True)
class CursorRunPolicy:
    model: str = "gpt-5.3-codex"
    reasoning: str = "medium"
    fast: bool = False
    work_on_current_branch: bool = False
    auto_create_pr: bool = False

    def validate(self) -> None:
        validate_cursor_request(
            model=self.model,
            reasoning=self.reasoning,
            fast=self.fast,
            work_on_current_branch=self.work_on_current_branch,
            auto_create_pr=self.auto_create_pr,
        )


class CursorBackend:
    name = "cursor"

    def __init__(self, policy: CursorRunPolicy) -> None:
        policy.validate()
        self.policy = policy

    def build_create_payload(self, *, prompt: str, repository_url: str, starting_ref: str) -> dict[str, object]:
        self.policy.validate()
        return {
            "prompt": {"text": prompt},
            "model": {
                "id": self.policy.model,
                "params": [
                    {"id": "reasoning", "value": self.policy.reasoning},
                    {"id": "fast", "value": "false"},
                ],
            },
            "repos": [{"url": repository_url, "startingRef": starting_ref}],
            "workOnCurrentBranch": False,
            "autoCreatePR": False,
        }
