from __future__ import annotations
from dataclasses import dataclass
import re, unicodedata
from .contracts import SourceEntityKey, ResolutionDecision

def normalize_name(value:str)->str:
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode('ascii').lower()
    return ' '.join(re.findall(r'[a-z0-9]+',value))

@dataclass(frozen=True)
class AliasRecord:
    entity_type:str; alias:str; canonical_id:str; source_system_id:str='*'

class EntityResolver:
    """Fail-closed exact/normalized alias starter. No probabilistic auto-linking."""
    def __init__(self, aliases):
        self._index={}
        for a in aliases:
            key=(a.source_system_id,a.entity_type,normalize_name(a.alias))
            self._index.setdefault(key,set()).add(a.canonical_id)
    def resolve(self, source_key:SourceEntityKey, display_name:str, decision_id:str)->ResolutionDecision:
        norm=normalize_name(display_name)
        candidates=set()
        for scope in (source_key.source_system_id,'*'):
            candidates |= self._index.get((scope,source_key.entity_type,norm),set())
        if len(candidates)==1:
            selected=next(iter(candidates)); state='RESOLVED'; method='NORMALIZED_ALIAS_EXACT'
        elif len(candidates)>1:
            selected=None; state='REVIEW_REQUIRED'; method='AMBIGUOUS_ALIAS'
        else:
            selected=None; state='UNRESOLVED'; method='NO_MATCH'
        return ResolutionDecision(decision_id,source_key,state,selected,method)
