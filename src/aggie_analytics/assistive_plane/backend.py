from __future__ import annotations

from typing import Protocol

from .contracts import AssistiveRequest, ProviderResult


class TransientBackendError(RuntimeError):
    """Retryable provider/network condition."""


class PermanentBackendError(RuntimeError):
    """Non-retryable authentication, policy, schema, or provider condition."""


class AssistiveBackend(Protocol):
    name: str

    def submit(self, request: AssistiveRequest, schema: dict[str, object]) -> ProviderResult:
        """Submit one already-admitted request and return a candidate result."""


class FakeBackend:
    name = "fake"

    def __init__(self, output: dict[str, object] | None = None) -> None:
        self.output = output or {}
        self.calls = 0

    def submit(self, request: AssistiveRequest, schema: dict[str, object]) -> ProviderResult:
        self.calls += 1
        return ProviderResult(
            provider=self.name,
            model_requested=request.model,
            model_resolved=request.model,
            output=self.output,
            usage={"input_tokens": 1, "output_tokens": 1},
            raw_response_id="fake-response",
            cost_usd="0.000001",
        )
