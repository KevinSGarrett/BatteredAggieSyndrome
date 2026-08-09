# Autonomous Research Threat Model and Safety Boundary

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Threats

The research plane is treated as capable but untrusted with respect to its own evaluation rules. Risks include metric shopping, protected-test peeking, threshold relaxation, scorecard deletion, label redefinition, future-data leakage, self-promotion, artifact substitution, experiment-spec mutation, search-history deletion, and runaway resource consumption.

## Controls

Controls include hash-sealed W17 rules, result-independent experiment IDs, development-only HPO, append-only queues, actor-role permissions, protected path denial, replay, artifact hashes, no-PROMOTE research state, bounded resource admission, wave ownership, and external promotion review.

## LLM/agent behavior

LLM-generated hypotheses, code and explanations are proposals. They cross the same data contracts, tests, replay and review gates as human-authored changes. Natural-language confidence is never evidence of predictive value.

## Prompt/source injection

External web/source text is untrusted data, not executable instruction. Research agents cannot execute source-provided commands, bypass authentication, or allow a source page to alter governance.

## Failure closed

If the W17 seal is invalid, a required threshold method is missing, a protected split is requested for HPO, or lineage cannot be resolved, the research action is blocked. The system does not default to permissive behavior.
