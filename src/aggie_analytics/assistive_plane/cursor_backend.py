from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .orchestration import validate_cursor_request


CURSOR_API_ROOT = "https://api.cursor.com/v1"


def load_cursor_key(authoritative_env: Path) -> str:
    matches: list[str] = []
    for line in authoritative_env.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "CURSOR_API_TOKEN":
            matches.append(value.strip().strip('"').strip("'"))
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError("CURSOR_API_TOKEN must exist exactly once and be nonempty")
    return matches[0]


class CursorApiError(RuntimeError):
    def __init__(self, status: int, code: str = "CURSOR_API_ERROR") -> None:
        super().__init__(f"{code}:HTTP_{status}")
        self.status = status


class CursorCloudClient:
    def __init__(self, authoritative_env: Path, *, timeout_seconds: int = 60) -> None:
        self.authoritative_env = authoritative_env
        self.timeout_seconds = timeout_seconds

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        token = load_cursor_key(self.authoritative_env)
        auth = base64.b64encode(f"{token}:".encode("ascii")).decode("ascii")
        wire = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{CURSOR_API_ROOT}{path}",
            data=wire,
            headers={"Authorization": f"Basic {auth}", "Accept": "application/json", "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise CursorApiError(exc.code) from exc


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

    def build_create_payload(self, *, prompt: str, repository_url: str, starting_ref: str, agent_id: str | None = None) -> dict[str, object]:
        self.policy.validate()
        payload: dict[str, object] = {
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
        if agent_id is not None:
            payload["agentId"] = agent_id
        return payload
