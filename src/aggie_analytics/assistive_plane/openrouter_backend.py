from __future__ import annotations

import json
import hashlib
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


def response_output_text(body: dict[str, object]) -> str | None:
    direct = body.get("output_text")
    if isinstance(direct, str):
        return direct
    output = body.get("output")
    if output is None:
        return None
    if not isinstance(output, list):
        raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_OUTPUT_CONTAINER")
    pieces: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_OUTPUT_ITEM")
        if item.get("type") != "message":
            continue
        content = item.get("content")
        if content is None:
            continue
        if not isinstance(content, list):
            raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_CONTENT_CONTAINER")
        for part in content:
            if not isinstance(part, dict):
                raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_CONTENT_ITEM")
            if part.get("type") == "output_text":
                text = part.get("text")
                if not isinstance(text, str):
                    raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_OUTPUT_TEXT")
                pieces.append(text)
    return "".join(pieces) if pieces else None


class OpenRouterBackend:
    name = "openrouter"

    def __init__(self, authoritative_env: Path, timeout_seconds: int = 60) -> None:
        self.authoritative_env = authoritative_env
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _payload(request: AssistiveRequest, schema: dict[str, object]) -> dict[str, object]:
        prompt = "\n\n".join(request.evidence_excerpts)
        payload: dict[str, object] = {
            "model": request.model,
            "input": prompt,
            "max_output_tokens": request.max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": request.task_id, "strict": True, "schema": schema}},
            "provider": {
                "require_parameters": True,
                "data_collection": "deny",
                "zdr": True,
                "allow_fallbacks": False,
            },
        }
        if request.reasoning_effort not in {"none", "minimal"}:
            payload["reasoning"] = {"effort": request.reasoning_effort}
        return payload

    def submit(self, request: AssistiveRequest, schema: dict[str, object]) -> ProviderResult:
        key = load_openrouter_key(self.authoritative_env)
        payload = self._payload(request, schema)
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
            provider_code = "UNKNOWN"
            try:
                error_body = json.loads(exc.read().decode("utf-8"))
                provider_code = str(error_body.get("error", {}).get("code", "UNKNOWN"))
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                pass
            error = TransientBackendError if exc.code == 429 or 500 <= exc.code < 600 else PermanentBackendError
            raise error(f"OPENROUTER_HTTP_{exc.code}_CODE_{provider_code}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise TransientBackendError("OpenRouter request failed with a transient transport error") from exc
        if not isinstance(body, dict):
            raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_TOP_LEVEL")
        usage = body.get("usage")
        if not isinstance(usage, dict):
            raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_USAGE")
        model_resolved = body.get("model")
        if not isinstance(model_resolved, str):
            raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_MODEL")
        raw_response_id = body.get("id")
        if not isinstance(raw_response_id, str):
            raise PermanentBackendError("OPENROUTER_RESPONSES_INVALID_ID")
        output_text = response_output_text(body)
        if not isinstance(output_text, str):
            raise PermanentBackendError("OPENROUTER_RESPONSES_MISSING_OUTPUT_TEXT")
        try:
            output = json.loads(output_text)
        except json.JSONDecodeError:
            output = {
                "_malformed_output": True,
                "output_text_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            }
        return ProviderResult(
            provider=self.name,
            model_requested=request.model,
            model_resolved=model_resolved,
            output=output,
            usage=dict(usage),
            raw_response_id=raw_response_id,
            cost_usd=str(usage.get("cost")) if usage.get("cost") is not None else None,
        )
