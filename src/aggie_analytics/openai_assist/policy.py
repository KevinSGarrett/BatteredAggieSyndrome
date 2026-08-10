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
        if self.payload.get("schema_version") != 2:
            raise PolicyError("unsupported OpenAI assist policy schema")
        if self.payload.get("governing_plan_sha256") != "651bbff29cb929cdc441178f67df59e87600a3bc8a54516a942562c7d09aa523":
            raise PolicyError("OpenAI policy is not bound to the current governing plan")
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
        budget = self.payload["budget"]
        required_allocations = {
            "CONTROLLER_SETUP", "NANO_BATCH", "FOUR_O_MINI_AB", "LUNA_HARD_VOLUME",
            "TERRA_COMPLEX", "SOL_GOLD_HARD", "EMBEDDINGS_RETRIEVAL",
            "CROSS_MODEL_QA", "VALUE_GATED_RESERVE",
        }
        if set(allocations) != required_allocations:
            raise PolicyError("balanced router allocations are incomplete or stale")
        if Decimal(allocations["TERRA_COMPLEX"]) != Decimal("15.00"):
            raise PolicyError("Terra base envelope must remain USD 15")
        if Decimal(allocations["SOL_GOLD_HARD"]) != Decimal("10.00"):
            raise PolicyError("Sol base envelope must remain USD 10")
        if Decimal(allocations["VALUE_GATED_RESERVE"]) != Decimal("22.00"):
            raise PolicyError("value-gated reserve must remain USD 22")
        if budget["model_caps"]["gpt-5.6-terra"] != {"base_usd": "15.00", "reserve_max_usd": "25.00"}:
            raise PolicyError("Terra model caps disagree with the governing plan")
        if budget["model_caps"]["gpt-5.6-sol"] != {"base_usd": "10.00", "reserve_max_usd": "17.00"}:
            raise PolicyError("Sol model caps disagree with the governing plan")
        if budget["initial_pilot_required_models"] != ["gpt-5.6-terra", "gpt-5.6-sol"]:
            raise PolicyError("initial pilot must include representative Terra and Sol calls")
        if budget["stage_limits_usd"] != ["10.00", "30.00", "60.00", "90.00", "100.00"]:
            raise PolicyError("staged budget release limits disagree with the governing plan")
        for name, model in self.payload["models"].items():
            if name not in {"gpt-5-nano", "gpt-4o-mini", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}:
                raise PolicyError(f"unapproved model in policy: {name}")
            if model["default_effort"] not in model["allowed_efforts"]:
                raise PolicyError(f"default effort is not allowed for {name}")
            if int(model["max_input_tokens"]) <= 0:
                raise PolicyError(f"invalid input limit for {name}")
        if set(self.payload["models"]) != {
            "gpt-5-nano", "gpt-4o-mini", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"
        }:
            raise PolicyError("balanced router model set is incomplete")

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
        if tokens.input_tokens > int(spec["max_input_tokens"]):
            raise PolicyError("estimated input exceeds the governed model context limit")
        long_context = tokens.input_tokens > int(spec.get("long_context_threshold_tokens", 10**18))
        if long_context:
            rate_key = (
                "long_context_batch_usd_per_million"
                if mode is ProcessingMode.BATCH
                else "long_context_standard_usd_per_million"
            )
        else:
            rate_key = "batch_usd_per_million" if mode is ProcessingMode.BATCH else "standard_usd_per_million"
        rates = spec[rate_key]
        uncached = max(0, tokens.input_tokens - tokens.cached_input_tokens)
        amount = (
            Decimal(uncached) * Decimal(rates["input"])
            + Decimal(tokens.cached_input_tokens) * Decimal(rates["cached_input"])
            + Decimal(tokens.max_output_tokens) * Decimal(rates["output"])
        ) / Decimal(1_000_000)
        return CostEstimate(amount, model, mode, tokens)
