from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path, PureWindowsPath
from typing import Any

from .contracts import CostEstimate, ProcessingMode, TokenEstimate


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class AssistivePolicy:
    root: Path
    payload: dict[str, Any]

    @classmethod
    def load(cls, repo_root: Path) -> "AssistivePolicy":
        path = repo_root / "configs" / "openai_assist_policy.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        policy = cls(repo_root, value)
        policy.validate()
        return policy

    @property
    def storage_root(self) -> Path:
        return Path(self.payload["storage"]["root"])

    @property
    def budget_limit(self) -> Decimal:
        return Decimal(self.payload["budget"]["absolute_usd"])

    def validate(self) -> None:
        if self.payload.get("schema_version") != 1:
            raise PolicyError("unsupported OpenAI assist policy schema")
        if self.payload.get("api", {}).get("store") is not False:
            raise PolicyError("Responses storage must be disabled")
        configured_storage = str(self.payload["storage"]["root"])
        native_absolute = self.storage_root.is_absolute()
        windows_absolute = PureWindowsPath(configured_storage).is_absolute()
        if not native_absolute and not windows_absolute:
            raise PolicyError("OpenAI storage root must be absolute")
        if native_absolute:
            try:
                self.storage_root.relative_to(self.root.resolve())
            except ValueError:
                pass
            else:
                raise PolicyError("OpenAI operational storage must remain outside Git")
        allocations = self.payload["budget"]["allocations"]
        if sum(Decimal(value) for value in allocations.values()) != self.budget_limit:
            raise PolicyError("budget allocations must sum to the absolute limit")
        if self.budget_limit != Decimal("100.00"):
            raise PolicyError("authorized absolute budget must remain USD 100")
        for name, model in self.payload["models"].items():
            if name not in {"gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}:
                raise PolicyError(f"unapproved model in policy: {name}")
            if model["default_effort"] not in model["allowed_efforts"]:
                raise PolicyError(f"default effort is not allowed for {name}")

    def model(self, name: str) -> dict[str, Any]:
        try:
            return self.payload["models"][name]
        except KeyError as exc:
            raise PolicyError(f"unapproved model: {name}") from exc

    def validate_route(self, model: str, effort: str) -> None:
        spec = self.model(model)
        if effort not in spec["allowed_efforts"]:
            raise PolicyError(f"reasoning effort {effort!r} is not allowed for {model}")

    def estimate_cost(
        self,
        model: str,
        mode: ProcessingMode,
        tokens: TokenEstimate,
    ) -> CostEstimate:
        spec = self.model(model)
        if tokens.input_tokens > int(spec["context_tokens"]):
            raise PolicyError("estimated input exceeds the governed model context limit")
        rate_key = "batch_usd_per_million" if mode is ProcessingMode.BATCH else "standard_usd_per_million"
        rates = spec[rate_key]
        uncached = max(0, tokens.input_tokens - tokens.cached_input_tokens)
        amount = (
            Decimal(uncached) * Decimal(rates["input"])
            + Decimal(tokens.cached_input_tokens) * Decimal(rates["cached_input"])
            + Decimal(tokens.max_output_tokens) * Decimal(rates["output"])
        ) / Decimal(1_000_000)
        return CostEstimate(amount, model, mode, tokens)
