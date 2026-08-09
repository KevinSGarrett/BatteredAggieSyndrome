# Wave 18 Research Operator Runbook

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Preflight

1. Verify W17 judging-rule seal.
2. Verify repository integrity and no forbidden artifacts.
3. Confirm owner wave/task readiness.
4. Confirm data/feature/model inputs exist and are hashable.
5. Confirm development-only split.
6. Confirm resource budget and paid-compute setting.

## Create experiment

Create a hypothesis or reference an approved existing hypothesis. Freeze the experiment spec. Compute canonical `EXP-*` identity. Insert it into the ExperimentStore. If an identical experiment already exists, inspect its lineage before scheduling a duplicate.

## Queue and run

Research governor approves. Scheduler admits based on dependencies/resources/locks. Worker runs in isolated worktree/source snapshot. Outputs go to experiment-local artifact paths. Worker produces development result packet and artifact manifest.

## Replay

A successful candidate is replayed from immutable inputs and W17 seal. Mismatch blocks adoption. A corrected configuration becomes a child experiment; the old failure remains in history.

## Tournament

Feature/model entrants are compared only when semantically compatible. Baselines are mandatory. Tournament result is research disposition, never direct production promotion.

## Adoption and handoff

Research governor may adopt a replay-verified candidate as challenger and produce `PROMOTION_REVIEW_REQUIRED`. Protected evaluation occurs outside the research feedback loop.

## Emergency stop

Stop all new execution if the W17 seal changes unexpectedly, the metadata store fails integrity, protected metrics appear in research result payloads, a secret/restricted artifact is detected, wave ownership is violated, or paid compute is requested without approval.
