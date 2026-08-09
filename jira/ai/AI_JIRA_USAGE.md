# AI Jira Usage

## Minimal retrieval sequence

1. Read `CURRENT_CONTEXT.md`.
2. Read `../index/READY_QUEUE.csv` or `READY_QUEUE_COMPACT.md`.
3. Select the highest valid READY **Subtask** compatible with the current execution lane/resources.
4. Open only that issue's canonical JSON or generated Markdown.
5. Open only `../sources/issue_source_manifests/<LOCAL_ID>.json`.
6. Verify source hashes/anchors, blockers, protected files, and expected outputs.
7. Execute the work in an isolated worktree when appropriate.
8. Run required tests and produce evidence with exact identities.
9. Apply `AI_COMPLETION_PROTOCOL.md` and `AI_SYNC_PROTOCOL.md`.
10. Recompute queues and validate.

Do **not** ingest the entire `jira/` directory into context. Indexes are retrieval maps, not documents to memorize. Do not execute Epics or Stories directly. Do not start hard-blocked, conditional, or deferred work merely because compute is idle.

## Query shortcuts

- Next valid work: `index/READY_QUEUE.csv`
- Why something is blocked: `index/BLOCKED_QUEUE.csv`
- Full issue lookup: `index/ISSUE_INDEX.csv`
- Source lookup: `index/SOURCE_REFERENCE_INDEX.csv`
- Dependency lookup: `index/DEPENDENCY_INDEX.csv`
- Requirement/control/ADR/test/artifact lookup: the corresponding traceability CSV.
- Exact execution packet: `ai/work_packets/<LOCAL_ID>.md`

## Execution versus aggregate packet contract


- Every `ACTIONABLE_POST_WAVE` record has `ai/work_packets/<LOCAL_ID>.md` and appears in `index/WORK_PACKET_INDEX.csv`.
- Only a packet whose canonical record is a `Subtask`, `execution_mode=ATOMIC_EXECUTION`, `ready=true`, and workflow `READY` may be selected for implementation.
- Epic/Story packets use `execution_mode=AGGREGATE_GATE`; they are review/integration/closure contracts and explicitly prohibit direct production mutation.
- Aggregate packets may write only their declared aggregate evidence manifest and synchronized Jira/local state after all child evidence and the integrated gate are verified.
- Historical records use `HISTORICAL_REFERENCE` and have no current execution packet.
