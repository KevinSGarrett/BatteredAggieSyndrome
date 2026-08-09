from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil
from .contracts import RawSnapshot

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def _iso(dt:datetime)->str:
    if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError('timestamps must be timezone-aware')
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

class RawSnapshotStore:
    """Content-addressed immutable raw store. Existing different bytes never overwrite."""
    def __init__(self, root:Path): self.root=root
    def ingest_file(self, source_id:str, dataset:str, input_path:Path, *, retrieved_at:datetime, source_uri:str, publication_time:datetime|None=None, row_count:int=0, schema_fields=(), metadata=None)->RawSnapshot:
        digest=_sha(input_path); sid=f"snap_{digest[:24]}"
        ext=input_path.suffix.lower() or '.bin'
        rel=Path('raw')/source_id/dataset/f'{sid}{ext}'
        dst=self.root/rel; dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists() and _sha(dst)!=digest: raise RuntimeError('immutable snapshot collision')
        if not dst.exists(): shutil.copyfile(input_path,dst)
        record={
          'snapshot_id':sid,'source_id':source_id,'dataset':dataset,'retrieved_at':_iso(retrieved_at),
          'publication_time':_iso(publication_time) if publication_time else None,'raw_sha256':digest,
          'relative_path':rel.as_posix(),'row_count':int(row_count),'schema_fields':list(schema_fields),
          'source_uri':source_uri,'metadata':metadata or {}
        }
        manifest=self.root/'manifests'/f'{sid}.json'; manifest.parent.mkdir(parents=True,exist_ok=True)
        encoded=json.dumps(record,sort_keys=True,indent=2)+'\n'
        if manifest.exists() and manifest.read_text(encoding='utf-8')!=encoded: raise RuntimeError('immutable manifest collision')
        manifest.write_text(encoded,encoding='utf-8')
        return RawSnapshot(sid,source_id,dataset,retrieved_at,digest,rel.as_posix(),int(row_count),tuple(schema_fields),source_uri,publication_time,metadata or {})
