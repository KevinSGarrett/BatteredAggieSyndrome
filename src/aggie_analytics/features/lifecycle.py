from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class FeatureState(str, Enum):
    CORE='CORE'; SUPPORTED='SUPPORTED'; CONDITIONAL='CONDITIONAL'; EXPERIMENTAL='EXPERIMENTAL'; REJECTED='REJECTED'; BANNED='BANNED'

REQUIRED_PROMOTION_EVIDENCE=frozenset({'PIT_SAFETY','SOURCE_DATA_QUALITY','TRANSFORM_LINEAGE','WALK_FORWARD_INCREMENTAL_VALUE','FAMILY_ABLATION','TEMPORAL_STABILITY','TARGET_SPECIFIC_VALUE','PROTECTED_CRITERIA_FROZEN','REPRODUCIBILITY'})

@dataclass(frozen=True)
class LifecycleEvidence:
    evidence_types: frozenset[str]
    governance_safety_correction: bool=False
    declared_condition: str|None=None

_ALLOWED={
 FeatureState.EXPERIMENTAL:{FeatureState.SUPPORTED,FeatureState.CONDITIONAL,FeatureState.REJECTED},
 FeatureState.SUPPORTED:{FeatureState.CORE,FeatureState.CONDITIONAL,FeatureState.EXPERIMENTAL,FeatureState.REJECTED},
 FeatureState.CORE:{FeatureState.SUPPORTED,FeatureState.CONDITIONAL,FeatureState.REJECTED},
 FeatureState.CONDITIONAL:{FeatureState.SUPPORTED,FeatureState.EXPERIMENTAL,FeatureState.REJECTED},
 FeatureState.REJECTED:{FeatureState.EXPERIMENTAL},
 FeatureState.BANNED:{FeatureState.EXPERIMENTAL},
}

def validate_transition(current: FeatureState, proposed: FeatureState, evidence: LifecycleEvidence) -> tuple[bool, tuple[str,...]]:
    findings=[]
    if proposed not in _ALLOWED.get(current,set()): findings.append('transition_not_allowed')
    if current is FeatureState.BANNED and proposed is FeatureState.EXPERIMENTAL and not evidence.governance_safety_correction:
        findings.append('banned_requires_governance_safety_correction')
    if proposed in {FeatureState.SUPPORTED,FeatureState.CORE,FeatureState.CONDITIONAL}:
        missing=sorted(REQUIRED_PROMOTION_EVIDENCE-set(evidence.evidence_types))
        if missing: findings.append('missing_promotion_evidence:'+','.join(missing))
    if proposed is FeatureState.CONDITIONAL and not evidence.declared_condition:
        findings.append('conditional_requires_declared_condition')
    return not findings, tuple(findings)
