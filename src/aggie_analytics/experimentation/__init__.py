"""Wave 18 experimentation and autonomous-research reference implementation.

No symbol in this package grants production promotion authority.  Protected
evaluation and champion/challenger promotion remain outside the research plane.
"""
from .lineage import canonical_json, content_hash, content_id, file_sha256
from .store import ExperimentStore
from .scheduler import ResourceRequest, ResourcePool, QueueCandidate, can_admit, select_admissible
from .feature_tournament import FeatureFamilyCandidate, FeatureTournamentEvidence
from .model_tournament import ModelEntrant, ModelTournamentPlan
from .replay_engine import ReplayInput, ReplayPlan
from .promotion_bridge import PromotionReviewPacket

__all__ = [
    "canonical_json","content_hash","content_id","file_sha256","ExperimentStore",
    "ResourceRequest","ResourcePool","QueueCandidate","can_admit","select_admissible",
    "FeatureFamilyCandidate","FeatureTournamentEvidence","ModelEntrant","ModelTournamentPlan",
    "ReplayInput","ReplayPlan","PromotionReviewPacket",
]
