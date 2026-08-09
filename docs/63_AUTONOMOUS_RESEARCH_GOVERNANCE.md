# Autonomous Research Governance

## Roles
The research plane separates:
- hypothesis proposer;
- research agent;
- research governor;
- scheduler;
- experiment worker;
- replay verifier;
- tournament coordinator;
- artifact curator;
- external W17 promotion reviewer.

No one role owns proposal, execution, replay, and promotion.

## Research agent may
- propose hypotheses, features, models, interactions, and search spaces;
- analyze development errors;
- create experiment specs;
- run approved development-only experiments;
- recommend rejection, inconclusive status, or challenger adoption.

## Research agent may not
- alter ground truth;
- alter W17 protected periods, metrics, scorecards, threshold methods, or promotion rules;
- change BAS definitions;
- use protected results as tuning feedback;
- change champion state;
- emit `PROMOTE`;
- initiate paid compute without explicit authorization.

## LLM proposals
LLM-generated code/hypotheses are untrusted proposals and cross the same review → experiment → replay → adoption → external promotion path.

## Judging-rule seal
`JRS-W17-001` is verified before execution and adoption. A mismatch blocks the action.

## Search-history governance
Failed trials, rejected experiments, dominated tournament entries, replay mismatches, abandoned hypotheses, and resource failures remain searchable.

## Stop/defer conditions
Autonomous research stops or defers when no approved hypothesis remains, budget is exhausted, required evidence is missing, rule seal fails, shared-contract ownership conflicts, repeated retries reproduce a known failure, or wave ownership does not authorize the work.

## User authority
The user may change protected project invariants or explicitly authorize paid compute. Idle hardware does not imply permission.
