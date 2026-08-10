from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import math
from typing import Callable, Iterable

from .contracts import ResolutionCandidate, SourceEntityKey
from .resolution import AliasRecord, normalize_name


ScoreFunction = Callable[[str, str], float]


def _rapidfuzz_ratio(left: str, right: str) -> float:
    try:
        fuzz = import_module("rapidfuzz.fuzz")
    except ModuleNotFoundError as exc:
        if exc.name != "rapidfuzz":
            raise
        raise RuntimeError("install the 'entity-resolution' optional dependency") from exc
    return float(fuzz.ratio(left, right))


@dataclass(frozen=True)
class FuzzyAliasCandidateGenerator:
    """Generate review candidates only; never create a resolution decision."""

    aliases: tuple[AliasRecord, ...]
    scorer: ScoreFunction = _rapidfuzz_ratio

    def generate(
        self,
        source_key: SourceEntityKey,
        display_name: str,
        *,
        minimum_diagnostic_score: float = 0.0,
        maximum_candidates: int = 10,
        evidence_capture_ids: Iterable[str] = (),
    ) -> tuple[ResolutionCandidate, ...]:
        if not 0.0 <= minimum_diagnostic_score <= 100.0:
            raise ValueError("minimum_diagnostic_score must be between 0 and 100")
        if maximum_candidates < 1:
            raise ValueError("maximum_candidates must be positive")
        query = normalize_name(display_name)
        evidence = tuple(evidence_capture_ids)
        best_by_canonical_id: dict[str, float] = {}
        for alias in self.aliases:
            if alias.entity_type != source_key.entity_type:
                continue
            if alias.source_system_id not in {"*", source_key.source_system_id}:
                continue
            score = float(self.scorer(query, normalize_name(alias.alias)))
            if not math.isfinite(score) or not 0.0 <= score <= 100.0:
                raise ValueError("candidate scorer must return a finite value between 0 and 100")
            if score >= minimum_diagnostic_score:
                best_by_canonical_id[alias.canonical_id] = max(
                    score, best_by_canonical_id.get(alias.canonical_id, -1.0)
                )
        ranked = sorted(best_by_canonical_id.items(), key=lambda item: (-item[1], item[0]))
        return tuple(
            ResolutionCandidate(
                source_key=source_key,
                candidate_canonical_id=canonical_id,
                mapping_method="RAPIDFUZZ_DIAGNOSTIC_CANDIDATE",
                evidence_capture_ids=evidence,
                diagnostic_score=score,
            )
            for canonical_id, score in ranked[:maximum_candidates]
        )
