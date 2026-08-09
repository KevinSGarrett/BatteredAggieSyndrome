# Wave 18 Full Acceptance and Traceability Matrix

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Completion definition

Wave 18 is complete only when the experiment identity, local store, append-only queue, tool-neutral tracking, HPO governance, feature tournament, model tournament, hypothesis lifecycle, worktree/resource isolation, judging-rule seal, replay, evidence packet, negative-result retention, challenger-adoption bridge and advanced-challenger gate are all represented by artifacts **and executable reference tests**.

## No empirical requirement

Wave 18 does not require a trained winner because W19/W20 materialization/model implementation is still ahead. Completion is therefore a reference/governance implementation gate, not a performance gate.

## Required negative tests

Tests must prove that protected splits cannot enter HPO, research roles cannot self-promote, W17 seal mutation is detected, duplicate experiment identities are handled, queue events cannot rewrite history, A&M model tournaments require TAMU-SP-00, pure/market lanes cannot be mixed accidentally, BAS label versions cannot drift, blocked temporal fields cannot enter feature tournaments, and advanced challengers remain blocked without baseline evidence.

## Coverage artifacts

`W18_MASTER_REQUIREMENT_COVERAGE.csv`, `W18_REQUIREMENT_TO_ARTIFACT_MATRIX.csv`, and `W18_TASK_TO_TEST_MATRIX.csv` provide machine-readable coverage. The full rebuild audit records the rejected prior W18 hashes and the final accepted hash after packaging.
