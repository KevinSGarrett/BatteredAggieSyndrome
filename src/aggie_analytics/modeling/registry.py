from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json, os, tempfile
from .runtime import ModelArtifact

@dataclass(frozen=True)
class RegistryRecord:
    artifact_sha256:str; model_id:str; model_version:str; model_family:str; target:str
    status:str; artifact_metadata_path:str; registered_at:str

class LocalModelRegistry:
    def __init__(self, root:Path): self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
    def register(self, artifact:ModelArtifact, *, status:str='CANDIDATE')->RegistryRecord:
        artifact.validate()
        if status not in {'CANDIDATE','DEVELOPMENT_ONLY','PROTECTED_READY','REJECTED','INCONCLUSIVE'}:
            raise ValueError('W20 registry status cannot self-promote')
        h=artifact.artifact_sha256; d=self.root/h; d.mkdir(parents=True,exist_ok=True)
        meta=d/'artifact.json'
        payload={'artifact_sha256':h,'model_id':artifact.model_id,'model_version':artifact.model_version,
                 'model_family':artifact.model_family,'target':artifact.target,'feature_names':list(artifact.feature_names),
                 'parameters':artifact.parameters,'training_data_ref':artifact.training_data_ref,
                 'training_cutoff':artifact.training_cutoff.isoformat(),'status':status,
                 'registered_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                 'metadata':dict(artifact.metadata)}
        if meta.exists():
            old=json.loads(meta.read_text());
            if old['artifact_sha256']!=h: raise RuntimeError('registry identity collision')
        else:
            fd,tmp=tempfile.mkstemp(dir=d,prefix='.artifact.',suffix='.tmp'); os.close(fd)
            Path(tmp).write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.replace(tmp,meta)
        return RegistryRecord(h,artifact.model_id,artifact.model_version,artifact.model_family,artifact.target,status,str(meta),payload['registered_at'])
