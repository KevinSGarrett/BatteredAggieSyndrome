from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from hashlib import sha256
import json, os, re, tempfile
from typing import Iterable, Mapping
from urllib.parse import urlsplit
from urllib.request import url2pathname

from .contracts import StepResult, WeeklyRunIdentity, stable_hash


class CheckpointConflict(RuntimeError):
    pass


class LocalCheckpointStore:
    """Durable single-machine checkpoint journal for W21.

    Every run directory is keyed by run_id. A run's immutable identity fingerprint
    must remain stable across retries. Step results are append-once by step id and
    identical retries are idempotent.
    """

    def __init__(self, root: Path, *, legacy_step_sha256: Mapping[str, str] | None = None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.legacy_step_sha256 = dict(legacy_step_sha256 or {})

    @staticmethod
    def _component(value: str) -> None:
        if (not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None
                or ".." in value or value.endswith(".") or PureWindowsPath(value).is_reserved()):
            raise ValueError("unsafe checkpoint identifier")

    def _run_dir(self, run_id: str) -> Path:
        self._component(run_id)
        d = self.root / run_id
        if d.is_symlink() or d.resolve().parent != self.root:
            raise ValueError("checkpoint run directory escapes root")
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
            if old != payload:
                raise CheckpointConflict("run_id already exists with different immutable identity")
            return True
        self._atomic_json(p, payload)
        return False

    def get(self, run_id: str, step_id: str) -> StepResult | None:
        self._component(step_id)
        p = self._run_dir(run_id) / "steps" / f"{step_id}.json"
        if p.is_symlink() or p.parent.is_symlink() or p.resolve().parent != self.root / run_id / "steps":
            raise ValueError("checkpoint step path escapes run directory")
        if not p.exists():
            return None
        raw = p.read_bytes()
        d = json.loads(raw)
        if "checkpoint_schema" in d:
            if d.pop("checkpoint_schema") != "aggie.step-checkpoint.v1" or d.pop("result_sha256", None) != stable_hash(d):
                raise CheckpointConflict("checkpoint result identity mismatch")
            if d.pop("run_id", None) != run_id or d.pop("run_fingerprint", None) != self._run_fingerprint(run_id):
                raise CheckpointConflict("checkpoint run identity mismatch")
        elif self.legacy_step_sha256.get(p.relative_to(self.root).as_posix()) != sha256(raw).hexdigest():
            raise CheckpointConflict("legacy checkpoint requires an exact artifact pin")
        result = StepResult(**d)
        self._validate_result(result)
        if result.step_id != step_id:
            raise CheckpointConflict("checkpoint step identity mismatch")
        return result

    def _run_fingerprint(self, run_id: str) -> str:
        path = self._run_dir(run_id) / "run.json"
        if path.is_symlink():
            raise CheckpointConflict("unsafe checkpoint run identity path")
        document = json.loads(path.read_bytes())
        fingerprint = document.pop("fingerprint", None)
        if (set(document) != {"run_id", "forecast_week", "as_of", "source_snapshot_refs", "metadata"}
                or document["run_id"] != run_id or stable_hash(document) != fingerprint):
            raise CheckpointConflict("checkpoint run identity mismatch")
        return fingerprint

    @staticmethod
    def _validate_result(result: StepResult) -> None:
        result.validate()
        LocalCheckpointStore._component(result.step_id)
        if result.state != "SUCCEEDED":
            return
        if (not isinstance(result.output_hash, str) or re.fullmatch(r"[0-9a-f]{64}", result.output_hash) is None
                or not isinstance(result.output_ref, str)):
            raise CheckpointConflict("successful checkpoint requires a SHA-256 output identity")
        if result.output_ref.startswith("memory:"):
            if result.output_ref != f"memory:{result.step_id}:{result.output_hash[:16]}":
                raise CheckpointConflict("memory output reference identity mismatch")
        elif result.output_ref.startswith("file:") or Path(result.output_ref).is_absolute():
            ref = result.output_ref
            if PureWindowsPath(ref).drive.startswith("\\\\"):
                raise CheckpointConflict("unsupported file output reference")
            if ref.startswith("file:"):
                parsed = urlsplit(ref)
                if parsed.netloc not in {"", "localhost"} or parsed.query or parsed.fragment:
                    raise CheckpointConflict("unsupported file output reference")
                ref = url2pathname(parsed.path)
            path = Path(ref)
            if not path.is_absolute() or not path.is_file() or sha256(path.read_bytes()).hexdigest() != result.output_hash:
                raise CheckpointConflict("checkpoint output artifact identity mismatch")
        # Other schemes (e.g. artifact:) are caller-owned logical references.
        # This store binds their exact recorded claim, not external artifact bytes.

    def record(self, run_id: str, result: StepResult) -> StepResult:
        self._validate_result(result)
        old = self.get(run_id, result.step_id)
        p = self._run_dir(run_id) / "steps" / f"{result.step_id}.json"
        payload = asdict(result)
        payload.update(run_id=run_id, run_fingerprint=self._run_fingerprint(run_id))
        payload = {**payload, "checkpoint_schema": "aggie.step-checkpoint.v1", "result_sha256": stable_hash(payload)}
        if old is not None:
            if stable_hash(asdict(old)) != stable_hash(asdict(result)):
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
            item = self.get(run_id, p.stem)
            if item.state == "SUCCEEDED":
                rows.append(item.step_id)
        return tuple(rows)

    def checkpoint_ref(self, run_id: str) -> str:
        d = self._run_dir(run_id)
        payload = []
        for p in sorted(x for x in d.rglob("*.json") if x.is_file()):
            payload.append((p.relative_to(d).as_posix(), stable_hash(json.loads(p.read_text(encoding="utf-8")))))
        return f"checkpoint:{run_id}:{stable_hash(payload)}"
