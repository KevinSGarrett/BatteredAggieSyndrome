# GitHub workflow Bugbot rules

Never use pull_request_target for untrusted code. Codex jobs must checkout the PR merge ref or an explicitly bound read-only diff, persist-credentials: false, contents: read on the execution job, and keep comment-writing permissions in a separate job. Do not print secret values or lengths. Do not apply patches from the review action.
