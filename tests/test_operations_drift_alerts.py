from __future__ import annotations

import copy
import hashlib
import unittest

from aggie_analytics.operations.drift_alerts import (
    AlertLedger,
    DRIFT_CLASSES,
    DriftObservation,
    DriftRule,
    evaluate_drift,
    validate_alert_snapshot,
    validate_drift_evaluation,
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def exact_rule(drift_class: str, *, severity: str = "HIGH") -> DriftRule:
    terms = drift_class == "TERMS_METADATA"
    return DriftRule(
        rule_id=f"{drift_class.lower()}-identity-v1",
        drift_class=drift_class,
        scope_id=f"scope/{drift_class.lower()}",
        rule_kind="EXACT_IDENTITY",
        baseline_value=digest(f"{drift_class}:baseline"),
        baseline_evidence_sha256=digest(f"{drift_class}:baseline-evidence"),
        severity="WARNING" if terms else severity,
        blocking_effect=(
            "METADATA_ONLY_NONBLOCKING" if terms else "QUARANTINE_AFFECTED_SCOPE"
        ),
    )


class DriftAlertTests(unittest.TestCase):
    def test_all_declared_drift_classes_detect_exact_identity_change(self) -> None:
        self.assertEqual(12, len(DRIFT_CLASSES))
        for drift_class in sorted(DRIFT_CLASSES):
            with self.subTest(drift_class=drift_class):
                rule = exact_rule(drift_class)
                evaluation = evaluate_drift(
                    rule,
                    DriftObservation(
                        value=digest(f"{drift_class}:changed"),
                        evidence_sha256=digest(f"{drift_class}:observation"),
                        observed_at_utc="2026-08-14T06:30:00Z",
                    ),
                    evaluated_at_utc="2026-08-14T06:30:01Z",
                )
                validate_drift_evaluation(evaluation)
                self.assertEqual("DRIFT", evaluation["status"])
                self.assertEqual(drift_class, evaluation["rule"]["drift_class"])
                if drift_class == "TERMS_METADATA":
                    self.assertEqual(
                        "METADATA_ONLY_NONBLOCKING", evaluation["blocking_effect"]
                    )

    def test_exact_match_is_no_drift_and_deterministic(self) -> None:
        rule = exact_rule("SCHEMA")
        observation = DriftObservation(
            value=digest("SCHEMA:baseline"),
            evidence_sha256=digest("schema:observation"),
            observed_at_utc="2026-08-14T06:30:00Z",
        )
        first = evaluate_drift(
            rule, observation, evaluated_at_utc="2026-08-14T06:30:01Z"
        )
        second = evaluate_drift(
            rule, observation, evaluated_at_utc="2026-08-14T06:30:01Z"
        )
        self.assertEqual(first, second)
        self.assertEqual("NO_DRIFT", first["status"])
        self.assertEqual("METADATA_ONLY_NONBLOCKING", first["blocking_effect"])

    def test_threshold_rules_require_versioned_threshold_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "threshold_source_sha256"):
            DriftRule(
                rule_id="freshness-v1",
                drift_class="FRESHNESS",
                scope_id="source/cfbd",
                rule_kind="MAX_AGE_SECONDS",
                baseline_value="2026-08-14T06:00:00Z",
                baseline_evidence_sha256=digest("freshness-baseline"),
                severity="HIGH",
                blocking_effect="QUARANTINE_AFFECTED_SCOPE",
                threshold=900,
            ).as_dict()

        rule = DriftRule(
            rule_id="freshness-v1",
            drift_class="FRESHNESS",
            scope_id="source/cfbd",
            rule_kind="MAX_AGE_SECONDS",
            baseline_value="2026-08-14T06:00:00Z",
            baseline_evidence_sha256=digest("freshness-baseline"),
            severity="HIGH",
            blocking_effect="QUARANTINE_AFFECTED_SCOPE",
            threshold=900,
            threshold_source_sha256=digest("observability-max-age-contract"),
        )
        fresh = evaluate_drift(
            rule,
            DriftObservation(
                value="2026-08-14T06:20:00Z",
                evidence_sha256=digest("fresh-capture"),
                observed_at_utc="2026-08-14T06:20:00Z",
            ),
            evaluated_at_utc="2026-08-14T06:30:00Z",
        )
        stale = evaluate_drift(
            rule,
            DriftObservation(
                value="2026-08-14T06:00:00Z",
                evidence_sha256=digest("stale-capture"),
                observed_at_utc="2026-08-14T06:20:00Z",
            ),
            evaluated_at_utc="2026-08-14T06:30:00Z",
        )
        self.assertEqual("NO_DRIFT", fresh["status"])
        self.assertEqual("DRIFT", stale["status"])

    def test_terms_metadata_cannot_be_reintroduced_as_private_research_gate(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "cannot block private research"):
            DriftRule(
                rule_id="terms-v1",
                drift_class="TERMS_METADATA",
                scope_id="source/public",
                rule_kind="BOOLEAN_INVARIANT",
                baseline_value=True,
                baseline_evidence_sha256=digest("terms"),
                severity="HIGH",
                blocking_effect="BLOCK_AFFECTED_TRAINING",
            ).as_dict()

    def test_dedup_ack_escalation_and_evidence_change_resolution(self) -> None:
        rule = exact_rule("SCHEMA", severity="WARNING")
        drift = evaluate_drift(
            rule,
            DriftObservation(
                value=digest("schema:changed"),
                evidence_sha256=digest("schema:changed-evidence"),
                observed_at_utc="2026-08-14T06:30:00Z",
            ),
            evaluated_at_utc="2026-08-14T06:30:01Z",
        )
        ledger = AlertLedger()
        alert_id = ledger.ingest(drift)
        self.assertEqual(alert_id, ledger.ingest(drift))
        ledger.acknowledge(
            alert_id,
            actor_id="operator-1",
            evidence_sha256=digest("ack-evidence"),
            occurred_at_utc="2026-08-14T06:31:00Z",
        )
        ledger.escalate(
            alert_id,
            to_severity="HIGH",
            escalation_rule_id="schema-escalation-v1",
            actor_id="policy-controller",
            evidence_sha256=digest("escalation-evidence"),
            occurred_at_utc="2026-08-14T06:32:00Z",
        )
        with self.assertRaisesRegex(ValueError, "clearing no-drift"):
            ledger.resolve(
                alert_id,
                clearing_evaluation=drift,
                actor_id="operator-1",
                evidence_sha256=digest("invalid-resolution"),
                occurred_at_utc="2026-08-14T06:33:00Z",
            )
        clearing = evaluate_drift(
            rule,
            DriftObservation(
                value=digest("SCHEMA:baseline"),
                evidence_sha256=digest("schema:clearing-evidence"),
                observed_at_utc="2026-08-14T06:34:00Z",
            ),
            evaluated_at_utc="2026-08-14T06:34:01Z",
        )
        ledger.resolve(
            alert_id,
            clearing_evaluation=clearing,
            actor_id="operator-1",
            evidence_sha256=digest("resolution-evidence"),
            occurred_at_utc="2026-08-14T06:35:00Z",
        )
        snapshot = ledger.snapshot()
        validate_alert_snapshot(snapshot)
        record = snapshot["records"][0]
        self.assertEqual("RESOLVED", record["status"])
        self.assertEqual(
            ["OPENED", "ACKNOWLEDGED", "ESCALATED", "RESOLVED"],
            [item["transition_type"] for item in record["transitions"]],
        )

    def test_evaluation_and_lifecycle_mutations_fail_closed(self) -> None:
        rule = exact_rule("SECURITY", severity="CRITICAL")
        evaluation = evaluate_drift(
            rule,
            DriftObservation(
                value=digest("security:changed"),
                evidence_sha256=digest("security:evidence"),
                observed_at_utc="2026-08-14T06:30:00Z",
            ),
            evaluated_at_utc="2026-08-14T06:30:01Z",
        )
        mutated = copy.deepcopy(evaluation)
        mutated["blocking_effect"] = "METADATA_ONLY_NONBLOCKING"
        with self.assertRaisesRegex(ValueError, "content identity"):
            validate_drift_evaluation(mutated)
        ledger = AlertLedger()
        ledger.ingest(evaluation)
        snapshot = ledger.snapshot()
        snapshot["records"][0]["status"] = "RESOLVED"
        with self.assertRaisesRegex(ValueError, "snapshot identity"):
            validate_alert_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
