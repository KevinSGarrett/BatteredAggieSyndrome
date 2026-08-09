# System Boundaries

## Boundary principle

A boundary exists when it protects a distinct invariant, failure domain, data contract or governance rule. A folder or deployable service is not created merely to make the architecture look sophisticated.

## Accepted bounded responsibilities

### Source adapters
Own provider-specific retrieval/parsing only. They may emit source envelopes and source-specific fields but must not embed football-model decisions.

### Immutable raw evidence
Owns exact fetched payload/file bytes plus retrieval metadata, content hashes and source provenance. Raw evidence is append-only.

### Validation and quarantine
Owns schema/contract checks, required-field checks, temporal metadata checks and quarantine decisions. Invalid data must not silently flow into canonical state.

### Canonicalization and entity resolution
Owns source-ID mapping into stable internal identities and normalized observations. Detailed schemas remain W07 work.

### PIT state
Owns "what could have been known when?" and effective-dated reconstruction. It is a hard boundary: feature code cannot bypass it to query arbitrary mutable source state.

### Feature factory
Owns feature definitions, lineage and train/inference feature parity. Feature promotion remains empirical.

### National modeling
Learns broad college-football behavior and emits national strength/forecast representations.

### A&M specialization
Consumes national representations plus higher-resolution A&M state. It may adapt/residualize/calibrate but may not fork entity truth or use A&M-only historical training as the national foundation.

### Forecast assembly
Owns coherent output composition: joint score/margin/win distributions, scenario integration and uncertainty propagation.

### BAS
Owns scientific underperformance outputs relative to valid pregame expectation. It consumes forecast/PIT-safe information and cannot create labels from in-sample hindsight.

### Evaluation and promotion
Owns protected walk-forward scoring and champion/challenger decisions. Research cannot rewrite these rules.

### Research
Owns hypotheses, experiment branches and candidate artifacts. It can propose but not self-promote.

### Snapshot publication
Creates immutable forecast artifacts linked to data/model/feature versions.

### Read-only serving
Exposes forecast snapshots. It does not compute raw features, resolve entities or retrain models on request.

### Orchestration/monitoring
Schedules and observes approved jobs. The specific framework remains W21/W23 work.

## Deployment boundary

All above responsibilities are **logical modules inside one deployable/local repository by default**. A future service split requires a demonstrated reason such as:
- independent scaling;
- separate security boundary;
- different reliability/latency requirement;
- multi-user concurrency;
- operational isolation that materially reduces risk.

Absent such evidence, keep the modular monolith.
