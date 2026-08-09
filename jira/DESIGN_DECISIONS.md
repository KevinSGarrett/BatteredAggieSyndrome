# Jira-System Design Decisions

1. **JSON is canonical; Markdown is generated.** This prevents manually divergent human/machine copies.
2. **Standard portable hierarchy only.** Epics contain Stories or historical Tasks; Stories contain Sub-tasks. Phases are metadata/components, not an assumed unsupported initiative type.
3. **Historical and post-wave work coexist.** Historical IDs/statuses remain visible and filterable; post-wave issues carry real completion obligations.
4. **No direct DONE conversion.** Workflow, maturity, and evidence are separate so a completed design/starter never becomes fabricated product completion.
5. **Atomic post-wave execution uses Sub-tasks.** Each has explicit outputs, tests, evidence, stop conditions, and a compact AI packet. Stories/Epics are integrated gates, not direct execution units.
6. **Source references are hash/anchor based.** Full documents are not duplicated across issues; shared canonical sources plus per-issue manifests minimize token/storage drift.
7. **Indexes/queues are deterministic derivatives.** AI sessions start from compact queues and open one issue/source set.
8. **Import is target-neutral.** The primary artifact is an ordered External System Import CSV with Issue ID/Parent; API/link payloads remain templates until real target fields/keys/link types are discovered.
9. **Links follow key reconciliation.** Hard-dependency links are created only after Jira assigns real keys, avoiding guessed key ordering.
10. **Conditional/deferred lanes stay outside core release.** Advanced challengers require admission evidence; live/in-game remains separately deferred and cannot block completion of the pregame product.
11. **Simple deterministic tooling.** Markdown, CSV, JSON/JSONL, JSON-compatible YAML, and stdlib Python are used; no database/service is required.
## DD-009 — Second-pass content-aware validation and derivative closure


The first-pass pack was structurally correct but did not make task specificity, test modality, traceability inheritance, source-anchor resolution, or derivative synchronization executable invariants. Schema v2 treats each as a release-blocking validation concern. Domain-gate inheritance avoids copying hundreds of governance IDs into every atomic task while still making effective context machine-resolvable. `files_to_inspect` and `files_expected_to_be_touched` are separated so an AI agent does not mistake broad source context for mutation authorization. All operational rebuild entry points now regenerate every derivative from canonical JSON.

## Packet-coverage decision

14. **All post-wave records have packets, but modes differ.** Atomic Subtasks are executable; Epic/Story packets are aggregate integration gates.
