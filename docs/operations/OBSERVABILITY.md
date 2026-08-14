# W23 Local Observability Contract

The local starter uses append-only JSONL events plus a small metrics registry. Events contain identifiers, state transitions, durations/counts and references—not raw source payloads. Sensitive key names and credential-like strings are redacted before serialization. Runtime environment evidence is captured separately with a strict safe-environment allowlist.

This deliberately avoids making an external metrics/logging service mandatory. W23 preserves an adapter boundary so W24+ operations may export the same structured events/metrics if actual single-host operations justify it.

## Versioned drift alerts

`aggie_analytics.operations.drift_alerts` provides the deterministic alert contract for
source, API, terms metadata, schema, entity, feature, data, model, concept, freshness,
security, and governance drift. Rules bind an affected scope, baseline evidence hash,
severity, and scoped effect. Numeric and freshness thresholds are invalid unless they
also bind a versioned evidence hash; the runtime does not invent a threshold to force
an alert or a passing result.

Alert deduplication is stable across repeated observations of the same rule and scope.
Acknowledgement, escalation, and resolution are immutable chained transitions.
Escalation requires a named policy rule and evidence hash. Resolution requires a new
no-drift evaluation whose evidence differs from the opening observation. Technical or
quality failures quarantine or block only their declared scope. Terms or rights changes
remain metadata-only and cannot block private research acquisition or training; raw
third-party publication remains disabled absent a separate future distribution review.

Build and validate the bounded contract evidence with:

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path
python -B tools/build_drift_alert_validation.py --repo-root .
python -B tools/validate_drift_alerts.py --repo-root .
```

The validation artifact proves the executable contract and deterministic fixtures. It
does not claim that a live provider refresh found zero drift, that monitoring has run
continuously, or that any scientific or production-readiness gate has passed.
