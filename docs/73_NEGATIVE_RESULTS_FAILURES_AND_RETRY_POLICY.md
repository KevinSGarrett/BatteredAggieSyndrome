# Negative Results, Failures & Retry Policy

## Failure classes
### Scientific
Candidate underperforms, destabilizes calibration, fails ablation/stability, or adds no incremental value.

### Data
Source missing, invalid, incomplete, temporally unsafe, or schema-incompatible.

### Infrastructure
Crash, OOM, disk exhaustion, interruption, or unavailable service.

### Reproducibility
Replay mismatch, environment mismatch, missing artifact, changed code/data hash.

### Governance
Rule-seal mismatch, unauthorized protected access, role violation, or unapproved paid compute.

## Retry rules
- infrastructure failure may retry the same identity when configuration is unchanged;
- configuration/resource changes create a child experiment;
- scientific rejection does not auto-retry;
- governance failure blocks until corrected/reviewed;
- replay mismatch cannot be hidden by a new result packet.

## Retention
Rejected/failed experiments remain indexed with failure class, reason, evidence, hypothesis, parent/child lineage, and retry eligibility.
