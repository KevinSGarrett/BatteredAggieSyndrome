from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Mapping

SCHEMA_VERSION = "aggie.operations.drift-alerts.v1"

DRIFT_CLASSES = frozenset(
    {
        "SOURCE",
        "API",
        "TERMS_METADATA",
        "SCHEMA",
        "ENTITY",
        "FEATURE",
        "DATA",
        "MODEL",
        "CONCEPT",
        "FRESHNESS",
        "SECURITY",
        "GOVERNANCE",
    }
)
RULE_KINDS = frozenset(
    {"EXACT_IDENTITY", "BOOLEAN_INVARIANT", "ABSOLUTE_DELTA", "MAX_AGE_SECONDS"}
)
SEVERITY_RANK = {"INFO": 0, "WARNING": 1, "HIGH": 2, "CRITICAL": 3}
BLOCKING_EFFECTS = frozenset(
    {
        "METADATA_ONLY_NONBLOCKING",
        "QUARANTINE_AFFECTED_SCOPE",
        "BLOCK_AFFECTED_TRAINING",
        "BLOCK_AFFECTED_PUBLICATION",
        "BLOCK_AFFECTED_PROTECTED_DECISION",
    }
)
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
SHA256 = re.compile(r"[0-9a-f]{64}")


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


def _utc(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _finite_number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result <= 0):
        raise ValueError(
            f"{field} must be finite and {'positive' if positive else 'nonnegative'}"
        )
    return result


@dataclass(frozen=True)
class DriftRule:
    rule_id: str
    drift_class: str
    scope_id: str
    rule_kind: str
    baseline_value: str | float | bool
    baseline_evidence_sha256: str
    severity: str
    blocking_effect: str
    threshold: float | None = None
    threshold_source_sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        rule_kind = self.rule_kind.upper()
        drift_class = self.drift_class.upper()
        severity = self.severity.upper()
        blocking_effect = self.blocking_effect.upper()
        _identifier(self.rule_id, "rule_id")
        _identifier(self.scope_id, "scope_id")
        if drift_class not in DRIFT_CLASSES:
            raise ValueError("unsupported drift class")
        if rule_kind not in RULE_KINDS:
            raise ValueError("unsupported drift rule kind")
        if severity not in SEVERITY_RANK:
            raise ValueError("unsupported severity")
        if blocking_effect not in BLOCKING_EFFECTS:
            raise ValueError("unsupported blocking effect")
        _sha256(self.baseline_evidence_sha256, "baseline_evidence_sha256")

        baseline_value: str | float | bool
        if rule_kind == "EXACT_IDENTITY":
            baseline_value = _sha256(self.baseline_value, "baseline_value")
        elif rule_kind == "BOOLEAN_INVARIANT":
            if not isinstance(self.baseline_value, bool):
                raise ValueError("boolean invariant requires a boolean baseline")
            baseline_value = self.baseline_value
        elif rule_kind == "ABSOLUTE_DELTA":
            baseline_value = _finite_number(self.baseline_value, "baseline_value")
        else:
            baseline_value = _utc(self.baseline_value, "baseline_value")

        threshold = self.threshold
        threshold_source = self.threshold_source_sha256
        if rule_kind in {"ABSOLUTE_DELTA", "MAX_AGE_SECONDS"}:
            threshold = _finite_number(threshold, "threshold", positive=True)
            threshold_source = _sha256(threshold_source, "threshold_source_sha256")
        elif threshold is not None or threshold_source is not None:
            raise ValueError("non-threshold rule cannot carry threshold fields")

        if drift_class == "TERMS_METADATA":
            if blocking_effect != "METADATA_ONLY_NONBLOCKING":
                raise ValueError("terms metadata drift cannot block private research")
            if SEVERITY_RANK[severity] > SEVERITY_RANK["WARNING"]:
                raise ValueError("terms metadata drift severity cannot exceed WARNING")

        payload = {
            "schema_version": SCHEMA_VERSION,
            "rule_id": self.rule_id,
            "drift_class": drift_class,
            "scope_id": self.scope_id,
            "rule_kind": rule_kind,
            "baseline_value": baseline_value,
            "baseline_evidence_sha256": self.baseline_evidence_sha256,
            "severity": severity,
            "blocking_effect": blocking_effect,
            "threshold": threshold,
            "threshold_source_sha256": threshold_source,
        }
        payload["rule_identity"] = canonical_sha256(payload)
        return payload


@dataclass(frozen=True)
class DriftObservation:
    value: str | float | bool
    evidence_sha256: str
    observed_at_utc: str

    def as_dict(self, rule_kind: str) -> dict[str, Any]:
        kind = rule_kind.upper()
        if kind == "EXACT_IDENTITY":
            value: str | float | bool = _sha256(self.value, "observation value")
        elif kind == "BOOLEAN_INVARIANT":
            if not isinstance(self.value, bool):
                raise ValueError("boolean invariant requires a boolean observation")
            value = self.value
        elif kind == "ABSOLUTE_DELTA":
            value = _finite_number(self.value, "observation value")
        elif kind == "MAX_AGE_SECONDS":
            value = _utc(self.value, "observation value")
        else:
            raise ValueError("unsupported drift rule kind")
        payload = {
            "value": value,
            "evidence_sha256": _sha256(
                self.evidence_sha256, "observation evidence_sha256"
            ),
            "observed_at_utc": _utc(self.observed_at_utc, "observed_at_utc"),
        }
        payload["observation_identity"] = canonical_sha256(payload)
        return payload


def evaluate_drift(
    rule: DriftRule,
    observation: DriftObservation,
    *,
    evaluated_at_utc: str,
) -> dict[str, Any]:
    rule_payload = rule.as_dict()
    observed = observation.as_dict(rule_payload["rule_kind"])
    evaluated_at = _utc(evaluated_at_utc, "evaluated_at_utc")
    kind = rule_payload["rule_kind"]
    baseline = rule_payload["baseline_value"]
    value = observed["value"]

    if kind in {"EXACT_IDENTITY", "BOOLEAN_INVARIANT"}:
        drifted = value != baseline
        delta: float | None = None
    elif kind == "ABSOLUTE_DELTA":
        delta = abs(float(value) - float(baseline))
        drifted = delta > float(rule_payload["threshold"])
    else:
        evaluated = datetime.fromisoformat(evaluated_at)
        observed_time = datetime.fromisoformat(str(value))
        delta = (evaluated - observed_time).total_seconds()
        drifted = delta < 0 or delta > float(rule_payload["threshold"])

    dedup_identity = canonical_sha256(
        {
            "rule_identity": rule_payload["rule_identity"],
            "drift_class": rule_payload["drift_class"],
            "scope_id": rule_payload["scope_id"],
        }
    )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "evaluation_type": "DRIFT_EVALUATION",
        "evaluated_at_utc": evaluated_at,
        "rule": rule_payload,
        "observation": observed,
        "status": "DRIFT" if drifted else "NO_DRIFT",
        "delta": delta,
        "severity": rule_payload["severity"] if drifted else "INFO",
        "blocking_effect": (
            rule_payload["blocking_effect"] if drifted else "METADATA_ONLY_NONBLOCKING"
        ),
        "dedup_identity": dedup_identity,
    }
    payload["evaluation_identity"] = canonical_sha256(payload)
    return payload


def validate_drift_evaluation(payload: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "evaluation_type",
        "evaluated_at_utc",
        "rule",
        "observation",
        "status",
        "delta",
        "severity",
        "blocking_effect",
        "dedup_identity",
        "evaluation_identity",
    }
    if set(payload) != required or payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("drift evaluation schema or field set mismatch")
    if payload["evaluation_type"] != "DRIFT_EVALUATION":
        raise ValueError("drift evaluation type mismatch")
    canonical = dict(payload)
    claimed = canonical.pop("evaluation_identity")
    if claimed != canonical_sha256(canonical):
        raise ValueError("drift evaluation content identity mismatch")

    rule_data = dict(payload["rule"])
    rule_identity = rule_data.pop("rule_identity", None)
    if rule_identity != canonical_sha256(rule_data):
        raise ValueError("drift rule content identity mismatch")
    rule = DriftRule(
        rule_id=rule_data["rule_id"],
        drift_class=rule_data["drift_class"],
        scope_id=rule_data["scope_id"],
        rule_kind=rule_data["rule_kind"],
        baseline_value=rule_data["baseline_value"],
        baseline_evidence_sha256=rule_data["baseline_evidence_sha256"],
        severity=rule_data["severity"],
        blocking_effect=rule_data["blocking_effect"],
        threshold=rule_data["threshold"],
        threshold_source_sha256=rule_data["threshold_source_sha256"],
    )
    if rule.as_dict() != payload["rule"]:
        raise ValueError("drift rule normalization mismatch")

    observed_data = dict(payload["observation"])
    observed_identity = observed_data.pop("observation_identity", None)
    if observed_identity != canonical_sha256(observed_data):
        raise ValueError("drift observation content identity mismatch")
    observation = DriftObservation(**observed_data)
    rebuilt = evaluate_drift(
        rule, observation, evaluated_at_utc=payload["evaluated_at_utc"]
    )
    if dict(payload) != rebuilt:
        raise ValueError("drift evaluation semantic mismatch")


class AlertLedger:
    """Deterministic in-memory lifecycle; callers own durable atomic persistence."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _transition(
        *,
        transition_type: str,
        occurred_at_utc: str,
        evidence_sha256: str,
        actor_id: str,
        previous_transition_identity: str | None,
        details: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "transition_type": _identifier(transition_type, "transition_type"),
            "occurred_at_utc": _utc(occurred_at_utc, "occurred_at_utc"),
            "evidence_sha256": _sha256(evidence_sha256, "transition evidence_sha256"),
            "actor_id": _identifier(actor_id, "actor_id"),
            "previous_transition_identity": previous_transition_identity,
            "details": dict(details),
        }
        if previous_transition_identity is not None:
            _sha256(previous_transition_identity, "previous_transition_identity")
        payload["transition_identity"] = canonical_sha256(payload)
        return payload

    def ingest(self, evaluation: Mapping[str, Any]) -> str:
        validate_drift_evaluation(evaluation)
        if evaluation["status"] != "DRIFT":
            raise ValueError("only drift evaluations create alerts")
        alert_id = str(evaluation["dedup_identity"])
        existing = self._records.get(alert_id)
        if existing is None:
            transition = self._transition(
                transition_type="OPENED",
                occurred_at_utc=evaluation["evaluated_at_utc"],
                evidence_sha256=evaluation["observation"]["evidence_sha256"],
                actor_id="detector",
                previous_transition_identity=None,
                details={"evaluation_identity": evaluation["evaluation_identity"]},
            )
            self._records[alert_id] = {
                "alert_id": alert_id,
                "rule_identity": evaluation["rule"]["rule_identity"],
                "scope_id": evaluation["rule"]["scope_id"],
                "status": "OPEN",
                "current_severity": evaluation["severity"],
                "opening_evaluation": dict(evaluation),
                "latest_evaluation": dict(evaluation),
                "transitions": [transition],
            }
            return alert_id
        if existing["status"] == "RESOLVED":
            raise ValueError("resolved alert cannot be silently reopened")
        if (
            existing["latest_evaluation"]["evaluation_identity"]
            == evaluation["evaluation_identity"]
        ):
            return alert_id
        transition = self._transition(
            transition_type="REOBSERVED",
            occurred_at_utc=evaluation["evaluated_at_utc"],
            evidence_sha256=evaluation["observation"]["evidence_sha256"],
            actor_id="detector",
            previous_transition_identity=existing["transitions"][-1][
                "transition_identity"
            ],
            details={"evaluation_identity": evaluation["evaluation_identity"]},
        )
        existing["latest_evaluation"] = dict(evaluation)
        existing["transitions"].append(transition)
        return alert_id

    def acknowledge(
        self,
        alert_id: str,
        *,
        actor_id: str,
        evidence_sha256: str,
        occurred_at_utc: str,
    ) -> None:
        record = self._active(alert_id)
        transition = self._transition(
            transition_type="ACKNOWLEDGED",
            occurred_at_utc=occurred_at_utc,
            evidence_sha256=evidence_sha256,
            actor_id=actor_id,
            previous_transition_identity=record["transitions"][-1][
                "transition_identity"
            ],
            details={},
        )
        record["status"] = "ACKNOWLEDGED"
        record["transitions"].append(transition)

    def escalate(
        self,
        alert_id: str,
        *,
        to_severity: str,
        escalation_rule_id: str,
        actor_id: str,
        evidence_sha256: str,
        occurred_at_utc: str,
    ) -> None:
        record = self._active(alert_id)
        severity = to_severity.upper()
        if severity not in SEVERITY_RANK:
            raise ValueError("unsupported escalation severity")
        if SEVERITY_RANK[severity] <= SEVERITY_RANK[record["current_severity"]]:
            raise ValueError("escalation must increase severity")
        transition = self._transition(
            transition_type="ESCALATED",
            occurred_at_utc=occurred_at_utc,
            evidence_sha256=evidence_sha256,
            actor_id=actor_id,
            previous_transition_identity=record["transitions"][-1][
                "transition_identity"
            ],
            details={
                "from_severity": record["current_severity"],
                "to_severity": severity,
                "escalation_rule_id": _identifier(
                    escalation_rule_id, "escalation_rule_id"
                ),
            },
        )
        record["current_severity"] = severity
        record["status"] = "ESCALATED"
        record["transitions"].append(transition)

    def resolve(
        self,
        alert_id: str,
        *,
        clearing_evaluation: Mapping[str, Any],
        actor_id: str,
        evidence_sha256: str,
        occurred_at_utc: str,
    ) -> None:
        record = self._active(alert_id)
        validate_drift_evaluation(clearing_evaluation)
        if clearing_evaluation["status"] != "NO_DRIFT":
            raise ValueError("resolution requires a clearing no-drift evaluation")
        if clearing_evaluation["dedup_identity"] != alert_id:
            raise ValueError("clearing evaluation does not match alert scope")
        opening_observation = record["opening_evaluation"]["observation"][
            "observation_identity"
        ]
        if (
            clearing_evaluation["observation"]["observation_identity"]
            == opening_observation
        ):
            raise ValueError("resolution requires changed evidence")
        transition = self._transition(
            transition_type="RESOLVED",
            occurred_at_utc=occurred_at_utc,
            evidence_sha256=evidence_sha256,
            actor_id=actor_id,
            previous_transition_identity=record["transitions"][-1][
                "transition_identity"
            ],
            details={
                "clearing_evaluation_identity": clearing_evaluation[
                    "evaluation_identity"
                ]
            },
        )
        record["latest_evaluation"] = dict(clearing_evaluation)
        record["status"] = "RESOLVED"
        record["transitions"].append(transition)

    def _active(self, alert_id: str) -> dict[str, Any]:
        _sha256(alert_id, "alert_id")
        if alert_id not in self._records:
            raise KeyError(alert_id)
        record = self._records[alert_id]
        if record["status"] == "RESOLVED":
            raise ValueError("alert is already resolved")
        return record

    def snapshot(self) -> dict[str, Any]:
        records = [self._records[key] for key in sorted(self._records)]
        payload = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "DRIFT_ALERT_LEDGER_SNAPSHOT",
            "records": json.loads(json.dumps(records, sort_keys=True)),
        }
        payload["snapshot_identity"] = canonical_sha256(payload)
        validate_alert_snapshot(payload)
        return payload


def validate_alert_snapshot(payload: Mapping[str, Any]) -> None:
    required = {"schema_version", "artifact_type", "records", "snapshot_identity"}
    if set(payload) != required or payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("alert snapshot schema or field set mismatch")
    if payload["artifact_type"] != "DRIFT_ALERT_LEDGER_SNAPSHOT":
        raise ValueError("alert snapshot type mismatch")
    canonical = dict(payload)
    claimed = canonical.pop("snapshot_identity")
    if claimed != canonical_sha256(canonical):
        raise ValueError("alert snapshot identity mismatch")
    records = payload["records"]
    if not isinstance(records, list):
        raise ValueError("alert snapshot records must be a list")
    alert_ids = [record.get("alert_id") for record in records]
    if alert_ids != sorted(alert_ids) or len(alert_ids) != len(set(alert_ids)):
        raise ValueError("alert snapshot records must be unique and sorted")
    for record in records:
        if set(record) != {
            "alert_id",
            "rule_identity",
            "scope_id",
            "status",
            "current_severity",
            "opening_evaluation",
            "latest_evaluation",
            "transitions",
        }:
            raise ValueError("alert record field set mismatch")
        _sha256(record["alert_id"], "alert_id")
        _sha256(record["rule_identity"], "rule_identity")
        _identifier(record["scope_id"], "scope_id")
        if record["status"] not in {"OPEN", "ACKNOWLEDGED", "ESCALATED", "RESOLVED"}:
            raise ValueError("alert record status invalid")
        if record["current_severity"] not in SEVERITY_RANK:
            raise ValueError("alert current severity invalid")
        validate_drift_evaluation(record["opening_evaluation"])
        validate_drift_evaluation(record["latest_evaluation"])
        if record["opening_evaluation"]["dedup_identity"] != record["alert_id"]:
            raise ValueError("alert opening evaluation mismatch")
        if record["latest_evaluation"]["dedup_identity"] != record["alert_id"]:
            raise ValueError("alert latest evaluation mismatch")
        transitions = record["transitions"]
        if not isinstance(transitions, list) or not transitions:
            raise ValueError("alert requires transitions")
        previous = None
        for transition in transitions:
            canonical_transition = dict(transition)
            identity = canonical_transition.pop("transition_identity", None)
            if identity != canonical_sha256(canonical_transition):
                raise ValueError("alert transition identity mismatch")
            if transition["previous_transition_identity"] != previous:
                raise ValueError("alert transition chain mismatch")
            _utc(transition["occurred_at_utc"], "transition occurred_at_utc")
            _sha256(transition["evidence_sha256"], "transition evidence_sha256")
            _identifier(transition["actor_id"], "transition actor_id")
            previous = identity
        if record["status"] == "RESOLVED":
            if transitions[-1]["transition_type"] != "RESOLVED":
                raise ValueError("resolved alert lacks terminal resolution")
            if record["latest_evaluation"]["status"] != "NO_DRIFT":
                raise ValueError("resolved alert lacks clearing evaluation")
        elif record["latest_evaluation"]["status"] != "DRIFT":
            raise ValueError("active alert latest evaluation must remain drifted")
