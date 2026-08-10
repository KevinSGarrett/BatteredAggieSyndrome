# OpenAI API Assistive Research and Data Engineering Contract

Status: active optional research plane. Budget authority: USD 100 absolute maximum.

## Authority boundary

The OpenAI API may accelerate evidence-backed extraction, entity candidate ranking, schema interpretation, quarantine classification, conflict reconciliation, source-route research, retrieval, development error analysis, and bounded review. It is not part of the deterministic forecast-critical path and is never a required runtime dependency.

Every result is untrusted candidate, review, quarantine, or rejected material until deterministic project validators accept it. OpenAI cannot directly write or control immutable raw captures, canonical entities, identity merges, PIT state, known-at timestamps, training features, labels, protected windows, model promotion, champion state, forecasts, BAS, Aggie Excess, or publication state. A model may extract only facts present in cited evidence. Missing or contradictory evidence must produce `UNKNOWN`, `NOT_PRESENT`, or `CONFLICT`; confidence is not a calibrated probability. Name-only entity merges and fabricated facts, timestamps, outcomes, statistics, metrics, or identities are forbidden.

## Controller and API contract

All calls flow through one governed local controller. New synchronous work uses the Responses API with `store: false`; non-urgent bulk work uses the Batch API and `/v1/responses`. Machine-consumed results use strict JSON Schema Structured Outputs. The controller owns credential discovery and redaction, task/model/reasoning routing, prompt and schema identity, budget admission, idempotency, retries, caching, content-addressed storage, provenance, deterministic validation, usage reporting, and cleanup. Scattered direct API calls are prohibited.

The controller reads only the nonempty `OPENAI_API_KEY` value from the authoritative repository `.env`; it never prints, logs, commits, copies, serializes, hashes as evidence, or sends that key as prompt content. Prompts are minimized to relevant cited excerpts. Credentials, cookies, authentication headers, private personal information, the whole data lake, large source trees, Git history, and protected evidence are excluded.

## Models and escalation

Routine extraction, classification, tagging, and straightforward normalization start with `gpt-5.6-luna` at `none` or `low`. Ambiguous entity work, schema reasoning, source conflicts, and complex gamebooks use `gpt-5.6-terra` at `low` or `medium`. `gpt-5.6-sol` at `medium` or `high` is reserved for gold/prompt work, hard adjudications, bounded independent review, and genuinely difficult scientific or architectural analysis. Luna escalates to Terra and Terra to Sol only when evidence, schema failures, ambiguity, disagreement, or local evaluation justifies it. Embeddings require measured superiority over deterministic retrieval or deduplication.

## Budget and storage

The append-only local usage ledger reserves worst-case cost before a call and settles actual token cost after it. Allocations are: $10 probes/prompt/evaluation, $25 Luna Batch, $20 Terra Batch, $12 Sol gold/hard work, $5 embeddings, $10 disagreement/rerun/adversarial QA, $8 autonomous opportunities, and $10 contingency/completion. Alerts are emitted once at $25, $50, $75, and $90. Low-priority admission stops at $90. The remaining $10 may be released only for validated high-value work, necessary retries, or useful in-flight completion. Settled plus outstanding reserved cost must never exceed $100.

Operational material lives outside Git under `C:\BatteredAggieSyndrome.data\openai\` in `requests`, `responses`, `batches`, `manifests`, `evals`, `quarantine`, `usage`, `runtime`, and `tmp`. Requests and responses are content-addressed. Manifests preserve Jira/task identity, source and capture hashes, prompt/schema/model/reasoning identity, estimated and actual usage/cost, evidence validation, output hash, and disposition. Batch output is downloaded, hashed, and validated locally; remote files are deleted after preservation when practical; abandoned local temporary files are cleaned.

## Evaluation and pilots

A local versioned evaluation corpus covers positive, negative, ambiguous, conflicting, schema-drift, PIT-sensitive, target-leakage, and abstention cases. It measures schema validity, field precision/recall, evidence accuracy, correct abstention, unsupported facts, entity top-k recall, false merges, repeat consistency, disagreement, cost per accepted record, review time saved, and quarantine rate. Hosted OpenAI Evals is not a project dependency.

Pilot A is historical gamebook-equivalent extraction. Pilot B assists unresolved entity review without replacing deterministic or human merge authority. Pilot C classifies quarantine and schema drift. Pilot D begins only when suitable timestamped injury/availability evidence exists. Each begins with a deterministic/human gold sample and capable-model reference, remains in shadow/candidate mode, and receives empirical acceptance criteria before promotion. Routine validated formats may move to Luna Batch; ambiguous failures go to Terra and only a small hard residue to Sol.

## Completion and nonclaims

Completion requires the controller, external storage, budget ledger, strict schemas, local evaluation harness, empirical model comparison, at least one useful bounded pilot, deterministic candidate validation, cleanup, and passing repository, provenance, Jira, secret, PIT, leakage, identity, and full-suite validation. API failure degrades to deterministic/local work and never globally blocks historical expansion. This integration does not establish historical completeness, production-model readiness, protected performance, A&M specialization lift, BAS, Aggie Excess, or any scientific result.
