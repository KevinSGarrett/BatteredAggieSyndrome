from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from .backend import PermanentBackendError, TransientBackendError
from .contracts import AssistiveRequest, ProviderResult


OPENROUTER_RESPONSES_ENDPOINT = "https://openrouter.ai/api/v1/responses"


def load_openrouter_key(authoritative_env: Path) -> str:
    matches: list[str] = []
    for line in authoritative_env.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "OPENROUTER_API_KEY":
            matches.append(value.strip().strip('"').strip("'"))
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError("OPENROUTER_API_KEY must exist exactly once and be nonempty")
    return matches[0]


class OpenRouterBackend:
    name = "openrouter"

    def __init__(self, authoritative_env: Path, timeout_seconds: int = 60) -> None:
        self.authoritative_env = authoritative_env
        self.timeout_seconds = timeout_seconds

    def submit(self, request: AssistiveRequest, schema: dict[str, object]) -> ProviderResult:
        key = load_openrouter_key(self.authoritative_env)
        prompt = "\n\n".join(request.evidence_excerpts)
        payload = {
            "model": request.model,
            "input": prompt,
            "max_output_tokens": request.max_output_tokens,
            "reasoning": {"effort": request.reasoning_effort},
            "text": {"format": {"type": "json_schema", "name": request.task_id, "strict": True, "schema": schema}},
            "provider": {
                "require_parameters": True,
                "data_collection": "deny",
                "zdr": True,
                "allow_fallbacks": False,
            },
        }
        wire = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        http_request = urllib.request.Request(
            OPENROUTER_RESPONSES_ENDPOINT,
            data=wire,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error = TransientBackendError if exc.code == 429 or 500 <= exc.code < 600 else PermanentBackendError
            raise error(f"OpenRouter request failed with HTTP {exc.code}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise TransientBackendError("OpenRouter request failed with a transient transport error") from exc
        output_text = body.get("output_text")
        if not isinstance(output_text, str):
            raise PermanentBackendError("OpenRouter Responses result has no output_text")
        return ProviderResult(
            provider=self.name,
            model_requested=request.model,
            model_resolved=str(body.get("model", "")),
            output=json.loads(output_text),
            usage=dict(body.get("usage", {})),
            raw_response_id=str(body.get("id", "")),
            cost_usd=str(body.get("usage", {}).get("cost")) if body.get("usage", {}).get("cost") is not None else None,
        )
