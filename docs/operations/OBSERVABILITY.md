# W23 Local Observability Contract

The local starter uses append-only JSONL events plus a small metrics registry. Events contain identifiers, state transitions, durations/counts and references—not raw source payloads. Sensitive key names and credential-like strings are redacted before serialization. Runtime environment evidence is captured separately with a strict safe-environment allowlist.

This deliberately avoids making an external metrics/logging service mandatory. W23 preserves an adapter boundary so W24+ operations may export the same structured events/metrics if actual single-host operations justify it.
