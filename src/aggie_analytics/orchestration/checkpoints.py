from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json, os, tempfile
from typing import Iterable

from .contracts import StepResult, WeeklyRunIdentity, stable_hash


class CheckpointConflict(RuntimeError):
    pass


class LocalCheckpointStore:
    """Durable single-machine checkpoint journal for W21.

    Every run directory is keyed by run_id. A run's immutable identity fingerprint
    must remain stable across retries. Step results are append-once by step id and
    identical retries are idempotent.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        if not run_id or any(x in run_id for x in ("/", "\\", "..")):
            raise ValueError("unsafe run_id")
        d = self.root / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _atomic_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        os.close(fd)
        Path(tmp).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def initialize(self, identity: WeeklyRunIdentity) -> bool:
        identity.validate()
        p = self._run_dir(identity.run_id) / "run.json"
        payload = {
            "run_id": identity.run_id,
            "forecast_week": identity.forecast_week,
            "as_of": identity.as_of.isoformat(),
            "source_snapshot_refs": list(identity.source_snapshot_refs),
            "metadata": dict(sorted(identity.metadata.items())),
            "fingerprint": identity.fingerprint,
        }
        if p.exists():
            old = json.loads(p.read_text(encoding="utf-8"))
            if old.get("fingerprint") != identity.fingerprint:
                raise CheckpointConflict("run_id already exists with different immutable identity")
            return True
        self._atomic_json(p, payload)
        return False

    def get(self, run_id: str, step_id: str) -> StepResult | None:
        p = self._run_dir(run_id) / "steps" / f"{step_id}.json"
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        return StepResult(d["step_id"], d["state"], d["output_ref"], d["output_hash"], d.get("detail", ""), d.get("metadata", {}))

    def record(self, run_id: str, result: StepResult) -> StepResult:
        result.validate()
        p = self._run_dir(run_id) / "steps" / f"{result.step_id}.json"
        payload = asdict(result)
        if p.exists():
            old = json.loads(p.read_text(encoding="utf-8"))
            if stable_hash(old) != stable_hash(payload):
                raise CheckpointConflict(f"step {result.step_id} already recorded with different result")
            return result
        self._atomic_json(p, payload)
        return result

    def completed_steps(self, run_id: str) -> tuple[str, ...]:
        d = self._run_dir(run_id) / "steps"
        if not d.exists():
            return ()
        rows = []
        for p in sorted(d.glob("*.json")):
            item = json.loads(p.read_text(encoding="utf-8"))
            if item.get("state") == "SUCCEEDED":
                rows.append(item["step_id"])
        return tuple(rows)

    def checkpoint_ref(self, run_id: str) -> str:
        d = self._run_dir(run_id)
        payload = []
        for p in sorted(x for x in d.rglob("*.json") if x.is_file()):
            payload.append((p.relative_to(d).as_posix(), stable_hash(json.loads(p.read_text(encoding="utf-8")))))
        return f"checkpoint:{run_id}:{stable_hash(payload)}"
