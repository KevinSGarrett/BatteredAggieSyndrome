from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json, os, tempfile

from .contracts import stable_hash


@dataclass(frozen=True)
class ProtectedPromotionDecision:
    candidate_artifact_sha256: str
    champion_artifact_sha256: str | None
    decision: str
    judging_rule_seal_hash: str
    protected_evidence_hash: str
    evaluator_id: str
    decided_at: datetime

    def validate(self) -> None:
        if self.decision not in {"PROMOTE", "RETAIN_CHAMPION", "REJECT", "INCONCLUSIVE"}:
            raise ValueError("invalid governed promotion decision")
        if not all((self.candidate_artifact_sha256, self.judging_rule_seal_hash, self.protected_evidence_hash, self.evaluator_id)):
            raise ValueError("protected promotion evidence is required")
        if self.decided_at.tzinfo is None:
            raise ValueError("decided_at must be timezone-aware")
        if self.decision == "PROMOTE" and self.candidate_artifact_sha256 == self.champion_artifact_sha256:
            raise ValueError("cannot promote the current champion as a challenger")

    @property
    def decision_hash(self) -> str:
        self.validate()
        return stable_hash({
            "candidate": self.candidate_artifact_sha256,
            "champion": self.champion_artifact_sha256,
            "decision": self.decision,
            "judging_rule_seal_hash": self.judging_rule_seal_hash,
            "protected_evidence_hash": self.protected_evidence_hash,
            "evaluator_id": self.evaluator_id,
            "decided_at": self.decided_at.isoformat(),
        })


class ChampionRegistry:
    """Immutable champion history + atomic current pointer.

    This object consumes a completed W17-governed decision. It does not calculate
    protected metrics and cannot infer promotion from development results.
    """
    def __init__(self, root: Path):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "history").mkdir(exist_ok=True)

    def current(self) -> str | None:
        p = self.root / "current.json"
        return json.loads(p.read_text(encoding="utf-8"))["artifact_sha256"] if p.exists() else None

    @staticmethod
    def _atomic(path: Path, payload: dict) -> None:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".champion.", suffix=".tmp"); os.close(fd)
        Path(tmp).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def apply(self, decision: ProtectedPromotionDecision) -> str | None:
        decision.validate()
        current = self.current()
        if decision.champion_artifact_sha256 != current:
            raise RuntimeError("promotion decision champion reference does not match registry current state")
        hp = self.root / "history" / f"{decision.decision_hash}.json"
        payload = {
            "decision_hash": decision.decision_hash,
            "candidate_artifact_sha256": decision.candidate_artifact_sha256,
            "prior_champion_artifact_sha256": current,
            "decision": decision.decision,
            "judging_rule_seal_hash": decision.judging_rule_seal_hash,
            "protected_evidence_hash": decision.protected_evidence_hash,
            "evaluator_id": decision.evaluator_id,
            "decided_at": decision.decided_at.isoformat(),
        }
        if not hp.exists(): self._atomic(hp, payload)
        if decision.decision == "PROMOTE":
            self._atomic(self.root / "current.json", {"artifact_sha256": decision.candidate_artifact_sha256, "decision_hash": decision.decision_hash})
            return decision.candidate_artifact_sha256
        return current

    def rollback(self, *, expected_current: str, restore_artifact_sha256: str, reason: str) -> str:
        if self.current() != expected_current:
            raise RuntimeError("rollback expected_current mismatch")
        if not restore_artifact_sha256 or not reason:
            raise ValueError("rollback target and reason required")
        payload = {"artifact_sha256": restore_artifact_sha256, "rollback_from": expected_current, "reason": reason,
                   "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
        rhash = stable_hash(payload)
        self._atomic(self.root / "history" / f"rollback-{rhash}.json", payload)
        self._atomic(self.root / "current.json", {"artifact_sha256": restore_artifact_sha256, "rollback_hash": rhash})
        return restore_artifact_sha256
