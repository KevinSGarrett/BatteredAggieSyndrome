from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from math import sqrt

class CompetitionLevel(str, Enum):
    FBS="FBS"; FCS="FCS"; DII="DII"; DIII="DIII"; NAIA="NAIA"; JUCO="JUCO"; OTHER="OTHER"

@dataclass(frozen=True)
class TranslationEstimate:
    source_level: CompetitionLevel
    translated_strength: float
    translation_uncertainty: float
    method_id: str
    def __post_init__(self) -> None:
        if self.translation_uncertainty < 0:
            raise ValueError("translation_uncertainty must be non-negative")

def affine_translation(raw_strength: float, *, scale: float, offset: float) -> float:
    """Parameterized cross-division candidate; W11 supplies no fixed penalty."""
    return raw_strength*scale + offset

def root_sum_square_uncertainty(*components: float) -> float:
    """Reference uncertainty aggregation candidate, not final W16 calibration."""
    if any(v < 0 for v in components):
        raise ValueError("uncertainty components must be non-negative")
    return sqrt(sum(v*v for v in components))
