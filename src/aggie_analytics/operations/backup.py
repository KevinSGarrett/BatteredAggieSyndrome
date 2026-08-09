from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib, json, os, tempfile, zipfile

FIXED=(1980,1,1,0,0,0)

def _sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def _safe(name: str) -> bool:
    p=PurePosixPath(name)
    return not p.is_absolute() and ".." not in p.parts and "\\" not in name and not (len(name)>1 and name[1]==":")

def create_backup(source: Path, output_zip: Path) -> dict:
    source=Path(source).resolve(); output_zip=Path(output_zip)
    if not source.is_dir(): raise ValueError("backup source must be a directory")
    entries=[]
    files=sorted((p for p in source.rglob("*") if p.is_file()), key=lambda p:p.relative_to(source).as_posix())
    for p in files:
        if p.is_symlink(): raise ValueError("symlink backup members are not supported")
        b=p.read_bytes(); entries.append({"path":p.relative_to(source).as_posix(),"bytes":len(b),"sha256":_sha(b)})
    manifest={"schema_version":"aggie.backup.v1","created_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),"source_name":source.name,"entries":entries}
    output_zip.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output_zip,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p,e in zip(files,entries):
            info=zipfile.ZipInfo("payload/"+e["path"],FIXED); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16; z.writestr(info,p.read_bytes())
        info=zipfile.ZipInfo("BACKUP_MANIFEST.json",FIXED); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16; z.writestr(info,json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest

def verify_backup(backup_zip: Path) -> dict:
    with zipfile.ZipFile(backup_zip) as z:
        for info in z.infolist():
            if not _safe(info.filename): raise ValueError(f"unsafe backup member: {info.filename}")
        manifest=json.loads(z.read("BACKUP_MANIFEST.json"))
        expected={"payload/"+e["path"]:e for e in manifest["entries"]}
        actual={i.filename for i in z.infolist() if i.filename.startswith("payload/") and not i.is_dir()}
        if actual != set(expected): raise ValueError("backup payload/manifest coverage mismatch")
        for name,e in expected.items():
            data=z.read(name)
            if len(data)!=int(e["bytes"]) or _sha(data)!=e["sha256"]: raise ValueError(f"backup integrity mismatch: {name}")
    return manifest

def restore_backup(backup_zip: Path, destination: Path, *, require_empty: bool=True) -> dict:
    manifest=verify_backup(backup_zip); destination=Path(destination)
    if destination.exists() and require_empty and any(destination.iterdir()): raise ValueError("restore destination must be empty")
    destination.mkdir(parents=True,exist_ok=True); root=destination.resolve()
    with zipfile.ZipFile(backup_zip) as z:
        for e in manifest["entries"]:
            rel=PurePosixPath(e["path"]); target=(destination/Path(*rel.parts)).resolve()
            if root!=target and root not in target.parents: raise ValueError("unsafe restore target")
            target.parent.mkdir(parents=True,exist_ok=True)
            fd,tmp=tempfile.mkstemp(dir=target.parent,prefix=".restore."); os.close(fd); Path(tmp).write_bytes(z.read("payload/"+e["path"])); os.replace(tmp,target)
    return manifest
