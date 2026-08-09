"""Wave 03 architecture contracts.

These modules describe and validate logical boundaries. They are not football
data/model implementations.
"""

from .contracts import AsOfContext, ExecutionLane, MarketLane
from .registry import ArchitectureRegistry, load_architecture_registry

__all__ = [
    "AsOfContext",
    "ExecutionLane",
    "MarketLane",
    "ArchitectureRegistry",
    "load_architecture_registry",
]
