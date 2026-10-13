# Reference helper integrity boundaries

The local W18/W21/operations helpers retain their reference scope. Passing these checks does not qualify a fitted model, activate automated research or release scientific holds.

## Checkpoints
New step files use `aggie.step-checkpoint.v1` and bind the entire result to the run ID and immutable run fingerprint. Loaded results must validate, match the requested step, and have a valid successful output identity. `memory:` references bind the recorded content-hash prefix; `file:` or absolute local-file references recheck SHA-256 bytes. Other logical references such as `artifact:` remain caller-owned claims; this store does not resolve external storage. Missing or changed local output refuses reuse. Failed and quarantined terminal records continue to stop blind retries.

An original unversioned checkpoint can be read with an explicit `legacy_step_sha256` map on `LocalCheckpointStore`, keyed by run-relative-to-store POSIX filename and separately retained file-byte hash. An absent map is not inferred from current files. The legacy pin authenticates the preserved local record, not an external artifact behind an opaque reference. No original checkpoint is automatically rewritten.

## Experiment store and HPO
`integrity_check` reconstructs canonical spec/result/replay hashes, record IDs and bindings, queue event hashes and contiguous allowed transitions, artifact-record identities and SQLite foreign keys. Reads and appends refuse a corrupt store before returning or extending its evidence. Replay status derives from boolean checks and the failure code, not a free-standing VERIFIED claim. The local database has no external sequence anchor: deletion of an entire terminal suffix with no remaining dependent reference cannot be detected merely by hashing the remaining valid prefix.

HPO marks a nonfinite objective as FAILED with `InvalidObjectiveError`, retaining its trial identity/count and the existing failure sentinel convention. A caller-specified failure value must be finite. A finite negative or zero objective remains a legitimate COMPLETE numerical result; neither state itself asserts scientific usefulness.

## Alert lifecycle
Alert scope and rule bind to the validated opening/latest evaluations. Status and severity derive from the ordered opening, acknowledgement, escalation, reobservation and terminal resolution transitions. The opening and current observation/clearing fields must match their retained evaluations. Terms-metadata alerts remain nonblocking and cannot escalate above WARNING. This verifies internal retained evidence consistency, not independent authenticity of an externally substituted, fully rebuilt history; the caller still owns durable persistence.
