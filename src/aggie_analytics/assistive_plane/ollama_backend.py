from __future__ import annotations

from dataclasses import dataclass

from .orchestration import validate_ollama_route


@dataclass(frozen=True)
class OllamaRoutePolicy:
    endpoint: str
    model: str
    model_digest: str
    max_loaded_models: int = 1
    parallel_requests: int = 1
    context_tokens: int = 4096

    def validate(self) -> None:
        validate_ollama_route(
            endpoint=self.endpoint,
            max_loaded_models=self.max_loaded_models,
            parallel_requests=self.parallel_requests,
            context_tokens=self.context_tokens,
            model_digest=self.model_digest,
        )

    def build_chat_payload(self, *, messages: list[dict[str, str]], schema: dict[str, object]) -> dict[str, object]:
        self.validate()
        return {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema,
            "options": {"temperature": 0, "num_ctx": self.context_tokens},
            "keep_alive": "0",
        }
