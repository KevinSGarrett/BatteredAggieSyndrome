# Architecture Change, Documentation, Release, Observability, and Rollback

The accepted W25 architecture is the default implementation target. It is not immune to evidence-driven improvement, but material change must be explicit, traceable, and reversible.

## Implementation within accepted design

No new ADR is normally required when the task:

- fills in an already accepted interface;
- fixes behavior to match an existing requirement/ADR;
- adds an implementation detail with no material contract/dependency/operational change;
- improves tests/docs without changing semantics.

Record important implementation decisions in the PR/task packet without manufacturing ADRs for every choice.

## Material architecture change

A change is material when it affects one or more of:

- service/module/data boundary;
- canonical schema/ID/PIT semantics;
- API/forecast/evidence contract;
- storage/queue/infrastructure/deployment topology;
- dependency or vendor lock-in;
- security/access model;
- evaluation/promotion/research separation;
- migration/backfill/compatibility strategy;
- resource/cost/operations model;
- multiple downstream tasks or shared contracts.

Use `templates/ARCHITECTURE_CHANGE_PROPOSAL.md` and create/update the appropriate ADR. Include:

1. current requirement/failure and evidence;
2. proposed change and affected requirements/ACs/contracts;
3. alternatives, including the smallest option and accepted current design;
4. measurable expected benefit;
5. complexity, security, rights, PIT, scientific, resource, vendor, and operational costs;
6. compatibility, migration/backfill, integration order, and rollback;
7. protected-governance impact and approval authority;
8. adoption/rejection conditions.

Do not casually rewrite protected contracts. If the proposal affects protected judging/PIT/canonical identity, the relevant authority/human gate applies.

## Anti-YAGNI architecture gate

Before adding a framework/service/database/queue/agent/orchestrator/model family, answer:

- Which current requirement needs it?
- What simpler existing approach demonstrably fails?
- What measurable benefit justifies it now?
- What new maintenance, security, cost, failure, and migration burden appears?
- How will it be tested, observed, rolled back, and removed?

If the answer is “future flexibility” alone, defer it.

## Documentation policy

Update documentation when the change modifies:

- behavior or user/operator expectations;
- interface/schema/event/configuration;
- architecture/decision/risk/assumption;
- source rights/access/provenance;
- operational command, deployment, backup, recovery, or observability;
- acceptance evidence or known limitation.

Do not force a doc edit for every inconsequential internal line. Do not create duplicate documents. Update the canonical source and link from pointers.

Historical records remain historical. Current pointer documents should clearly supersede stale operational instructions.

## Change traceability

A material change should update, as applicable:

- Jira issue/source map;
- requirement and task traceability;
- ADR and ADR-acceptance mapping;
- acceptance status/evidence;
- schema/config versions and consumers;
- tests/fixtures;
- provenance/manifest/changelog;
- PR migration/rollback/limitations.

Do not update machine registries partially and leave prose/tests behind.

## Observability requirements

Production/weekly operations should expose enough evidence to answer:

- what source snapshots and cutoff were used;
- pipeline step/status/duration/resource usage;
- data freshness, schema/volume/missingness/source drift;
- entity-resolution/PIT/leakage gate outcomes;
- model/feature/version and uncertainty/OOD state;
- publication identity and serving freshness;
- failure/retry/resume and rollback state;
- security/access anomalies and cost where relevant.

Logs must be structured, bounded, redacted, and linked to run/artifact IDs. Avoid dumping raw restricted payloads.

## Backup and restore

For stateful data/artifacts/configuration:

- define what is backed up, location/classification, retention, encryption/access, and owner;
- test restore, not only backup creation;
- record recovery point/objective only from evidence;
- preserve immutable source/forecast/artifact identity;
- avoid backing up secrets into ordinary artifacts;
- validate restored state through repository/data/product checks.

## Rollback policy

Every change with material user/data/schema/model/operational impact needs a rollback or forward-fix plan:

- trigger/decision authority;
- previous known-good code/config/data/model/snapshot;
- compatibility of persisted state;
- steps and validation;
- data-loss/side-effect risk;
- communication/Jira/incident record;
- re-entry criteria.

Never “rollback” by deleting unknown data, resetting history, or overwriting immutable snapshots.

## Release readiness

Use `templates/RELEASE_READINESS_CHECKLIST.md` and `policies/release_readiness.json`.

A release requires:

- fixed scope/version/release notes;
- required CI/repository/security/dependency/source-rights gates;
- data/model/evaluation provenance where applicable;
- immutable artifact IDs and reproducibility;
- backup/restore and rollback validation;
- observability/freshness/error behavior;
- target-resource evidence for hardware-sensitive operation;
- accepted known limitations;
- annotated immutable release tag and reproducible artifacts.

Production release/rollback is HUMAN REQUIRED by default until a separately approved automated release policy exists.

## Tag policy

Use annotated, immutable, SemVer-like tags only for defined releases. Do not tag each task/PR. Never move or reuse a release tag; issue a new version if correction is required.
