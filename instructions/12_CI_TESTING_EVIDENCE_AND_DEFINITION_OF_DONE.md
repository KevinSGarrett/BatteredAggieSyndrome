# CI, Progressive Testing, Evidence, and Definition of Done

Testing must be proportional during implementation and comprehensive at the correct integration/scientific/release boundary. Running everything after every tiny edit wastes resources; running too little before integration hides risk.

Machine companions: `policies/test_tiers.json` and `policies/definition_of_done.json`.

## Progressive testing tiers

### Tier 1 — edit feedback

Run the narrowest check that exercises the changed behavior:

- one unit test or test class;
- one validator for a modified registry/schema;
- import/compile/static check;
- one fixture/replay example.

Use during implementation. Do not run the entire suite after each line.

### Tier 2 — impacted subsystem

Before a coherent commit or material PR update, run:

- affected package/unit tests;
- producer/consumer integration tests;
- schema/contract validator;
- regression tests for the defect/acceptance path;
- relevant Windows/Linux behavior if platform-sensitive.

### Tier 3 — PR readiness

Before Ready/merge, run applicable repository-level gates. Changes to instructions, governance, shared contracts, CI, repository tooling, manifests, or broad code normally require:

```powershell
python -B tools/validate_autonomous_controls.py --repo-root . --strict
python -B tools/validate_jira_control_plane.py --repo-root . --strict
python -B tools/validate_w25_final.py --repo-root .
python -B tools/validate_repository.py --repo-root . --strict
python -B -m unittest discover -s tests -v
python -B -W error -m unittest discover -s tests -v
```

The warning-strict suite is a PR-readiness/release gate, not a replacement for focused implementation tests. It prevents ignored resource, deprecation, subprocess, and archive warnings from being normalized into release evidence.

Domain changes also run their existing targeted validators and product/operations gates.

### Tier 4 — scientific/release/major integration

Run the complete applicable boundary suite:

- real chronological PIT replay and leakage batteries;
- protected evaluation/calibration/promotion;
- source contract/schema/population checks;
- E2E weekly pipeline/idempotency/resume;
- immutable publication/snapshot-only serving;
- target-hardware benchmark;
- backup/restore, rollback, observability/freshness/security;
- release-readiness checklist.

Synthetic starter tests are contract evidence, not substitutes for real-data or target-hardware evidence.

## Test selection by change surface

| Change | Minimum impacted evidence |
|---|---|
| Local pure function | direct unit tests + callers if behavior changes |
| Schema/registry | schema validator, readers/writers, migration/compatibility tests |
| PIT/feature | temporal eligibility, target-game exclusion, replay/leakage tests |
| Data adapter/source | contract tests, snapshot/provenance, rights/access status, missingness/error behavior |
| Model/calibration | baseline comparison, chronological split, calibration/coherence/uncertainty, protected judge separation |
| BAS/A&M | cross-fit, national no-adjustment baseline, peer/regime/null-result tests |
| Orchestration | idempotency, checkpoints/resume, partial failure, immutable publication |
| Product/API | snapshot-only reads, freshness, contract/version, security/error handling |
| Repository controls | instruction/Jira/repository validators, full unit suite, packaging verification |
| Operations/release | target benchmark if relevant, backup/restore, rollback, observability, security |

## Failed CI procedure

1. Identify exact failed job, step, command, OS/Python version, and head SHA.
2. Determine deterministic code failure, flaky/transient service, environment/dependency, permission, or configuration.
3. Reproduce locally or inspect complete logs.
4. Change the hypothesis/implementation/environment before rerunning a deterministic failure.
5. Retry a credible transient failure once.
6. Record external/flaky failures and block/escalate after the retry policy.
7. Do not repeatedly press rerun to obtain a green result.

## Evidence quality

Good evidence is:

- attributable to an exact code/data/config/version and command;
- reproducible or immutable where required;
- generated under the correct protocol and cutoff;
- honest about environment, limitations, and failure;
- linked to acceptance controls and the PR/Jira issue;
- small enough to review or stored in the approved artifact location.

Bad evidence includes screenshots without identifiers, edited logs, unstated manual steps, fabricated sample data presented as real, passing tests after weakening assertions, or protected results used to tune the candidate.

## Canonical Definition of Done

Every task must satisfy all applicable checks:

1. Jira acceptance criteria are satisfied or explicitly changed by authorized scope governance.
2. The coherent required implementation/deliverable exists and matches accepted design.
3. Focused/impacted tests and required repository/CI gates pass.
4. PIT/leakage/identity/protected judging/promotion rules remain intact.
5. Security, secrets, dependency, source-rights, and data policy pass.
6. Changed behavior/interfaces/operations/architecture have proportionate canonical documentation.
7. REQ/ADR/AC/provenance/Jira/PR traceability is updated where applicable.
8. No fabricated data/result/metric/threshold/BAS effect/A&M lift/benchmark/maturity claim exists.
9. No unexplained staged/unstaged/untracked files remain in the owned worktree.
10. The PR is complete, linked, reviewed, and free of unresolved CI/review/blocker.
11. Integration is complete through the approved path or a non-code outcome has accepted evidence.
12. Jira reflects the real final state with concise evidence.
13. Branch/worktree cleanup is complete or intentionally owned/deferred.
14. Known limitations and legitimate follow-ups are explicit.
15. Rollback/recovery implications are understood.

## Conditional Done requirements

### Data/source

Access/rights verified; immutable snapshot/manifests/provenance exist; restricted raw data remains local; failure/missingness is explicit.

### PIT/feature

Known-at and target-game exclusion pass real replay/leakage checks; missing evidence is not converted into false healthy/negative state.

### Model/ML

Strong baselines, chronological evaluation, calibration, reproducibility, protected promotion, and null-result honesty.

### A&M/BAS

National no-adjustment baseline retained; cross-fit/peer/regime/calibration/null-result protocol; no presumed nonzero effect.

### Schema/API

Compatibility/versioning/migration/consumer impact and rollback.

### Operations/release

Observability, backup/restore, freshness, resource evidence, rollback, and release readiness.

## Not Done

A task is not Done because:

- code was written;
- a Draft PR was opened;
- a synthetic fixture passed;
- CI was rerun until green without diagnosis;
- Jira status was changed;
- follow-up work required for acceptance was hidden in prose;
- a starter interface was labeled production-ready.

Use the PR-ready and merge-ready checklists.
