from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib, json, os, platform, shutil, subprocess, time, tracemalloc
from typing import Callable

@dataclass(frozen=True)
class TargetProfile:
    os_family: str = "Windows"
    cpu_contains: str = "Ryzen"
    min_ram_gib: float = 28.0
    gpu_contains: str = "RTX 5060"


def _ram_gib() -> float | None:
    try:
        if platform.system() == "Windows":
            import ctypes
            class M(ctypes.Structure):
                _fields_=[("length",ctypes.c_ulong),("memory_load",ctypes.c_ulong),("total_phys",ctypes.c_ulonglong),("avail_phys",ctypes.c_ulonglong),("total_page",ctypes.c_ulonglong),("avail_page",ctypes.c_ulonglong),("total_virtual",ctypes.c_ulonglong),("avail_virtual",ctypes.c_ulonglong),("avail_extended",ctypes.c_ulonglong)]
            m=M(); m.length=ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); return m.total_phys/(1024**3)
        pages=os.sysconf("SC_PHYS_PAGES"); size=os.sysconf("SC_PAGE_SIZE"); return pages*size/(1024**3)
    except Exception: return None


def _gpu_name() -> str | None:
    exe=shutil.which("nvidia-smi")
    if not exe: return None
    try:
        return subprocess.check_output([exe,"--query-gpu=name","--format=csv,noheader"],text=True,timeout=4).splitlines()[0].strip()
    except Exception: return None


def _bench(fn: Callable[[], object]) -> dict:
    tracemalloc.start(); start=time.perf_counter(); result=fn(); elapsed=time.perf_counter()-start; current,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    return {"seconds": round(elapsed,6), "python_peak_mib": round(peak/(1024**2),3), "result_sha256": hashlib.sha256(repr(result).encode()).hexdigest()}


def run_benchmark(*, profile: str = "smoke", target: TargetProfile | None = None) -> dict:
    target=target or TargetProfile(); n=5_000 if profile=="smoke" else 100_000
    rows=[{"game_id":f"g{i}","team":i%133,"value":(i*17)%101,"known_at":i} for i in range(n)]
    benches={
      "json_roundtrip": _bench(lambda: json.loads(json.dumps(rows,sort_keys=True))),
      "content_hash": _bench(lambda: hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()),
      "group_aggregate": _bench(lambda: {k:sum(r["value"] for r in rows if r["team"]==k) for k in range(133)}),
    }
    ram=_ram_gib(); gpu=_gpu_name(); cpu=platform.processor() or platform.machine()
    target_match=(platform.system()==target.os_family and target.cpu_contains.lower() in cpu.lower() and ram is not None and ram>=target.min_ram_gib and gpu is not None and target.gpu_contains.lower() in gpu.lower())
    return {
      "schema_version":"aggie.local_benchmark.v1", "captured_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
      "profile":profile, "host":{"platform":platform.platform(),"system":platform.system(),"cpu":cpu,"cpu_count":os.cpu_count(),"ram_gib":ram,"gpu":gpu},
      "declared_target":asdict(target), "target_match":target_match, "authoritative_for_thr_011_012":bool(target_match and profile=="representative"),
      "workloads":benches,
      "interpretation":"Authoritative only when representative profile runs on declared target hardware; otherwise smoke evidence only."
    }
