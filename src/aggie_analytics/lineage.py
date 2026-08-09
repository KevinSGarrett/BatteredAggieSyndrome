from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import hashlib, json
@dataclass(frozen=True)
class LineageRecord:
    lineage_id:str; artifact_type:str; output_id:str; parent_ids:tuple[str,...]; transform:str; metadata:dict[str,Any]

def make_lineage(artifact_type:str, output_id:str, parent_ids, transform:str, metadata=None)->LineageRecord:
    parents=tuple(sorted(str(x) for x in parent_ids)); body={'artifact_type':artifact_type,'output_id':output_id,'parent_ids':parents,'transform':transform,'metadata':metadata or {}}
    digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]
    return LineageRecord(f'lin_{digest}',artifact_type,output_id,parents,transform,metadata or {})
