from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .orchestration import validate_cursor_request


CURSOR_API_ROOT = "https://api.cursor.com/v1"
CURSOR_AGENT_ID_NAMESPACE = uuid.UUID("c7959537-257f-53a6-887b-3e8d00e0846f")


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


def cursor_agent_identity(job_id: str) -> str:
    if len(job_id) != 64 or any(character not in "0123456789abcdef" for character in job_id.lower()):
        raise ValueError("CURSOR_JOB_IDENTITY_INVALID")
    return f"bc-{uuid.uuid5(CURSOR_AGENT_ID_NAMESPACE, job_id.lower())}"


class CursorApiError(RuntimeError):
    def __init__(
        self,
        status: int,
        code: str = "CURSOR_API_ERROR",
        message: str = "",
        *,
        help_url: str = "",
        provider: str = "",
        request_id: str = "",
    ) -> None:
        detail = f":{message}" if message else ""
        super().__init__(f"{code}:HTTP_{status}{detail}")
        self.status = status
        self.code = code
        self.message = message
        self.help_url = help_url
        self.provider = provider
        self.request_id = request_id

    def evidence(self) -> dict[str, object]:
        return {
            "status": self.status,
            "code": self.code,
            "message": self.message,
            "help_url": self.help_url,
            "provider": self.provider,
            "request_id": self.request_id,
        }


def _safe_error_text(value: Any, *, maximum: int = 512) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    return normalized[:maximum]


def _cursor_api_error(exc: urllib.error.HTTPError) -> CursorApiError:
    payload: dict[str, Any] = {}
    try:
        decoded = json.loads(exc.read().decode("utf-8"))
        if isinstance(decoded, dict):
            payload = decoded
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        payload = {}
    error = payload.get("error", {})
    if not isinstance(error, dict):
        error = {}
    request_id = ""
    if exc.headers is not None:
        request_id = _safe_error_text(
            exc.headers.get("X-Request-ID") or exc.headers.get("X-Cursor-Request-ID") or "",
            maximum=128,
        )
    return CursorApiError(
        exc.code,
        _safe_error_text(error.get("code"), maximum=128) or "CURSOR_API_ERROR",
        _safe_error_text(error.get("message")),
        help_url=_safe_error_text(error.get("helpUrl")),
        provider=_safe_error_text(error.get("provider"), maximum=128),
        request_id=request_id,
    )


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
            raise _cursor_api_error(exc) from exc


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

    def build_followup_payload(self, *, prompt: str) -> dict[str, object]:
        self.policy.validate()
        if not prompt.strip():
            raise ValueError("CURSOR_FOLLOWUP_PROMPT_REQUIRED")
        return {"prompt": {"text": prompt}, "mode": "agent"}
