# Credentials and Secrets Contract

Credential values belong outside Git. Runtime and authorized control-plane processes receive them from the host environment or an ignored local launcher environment. Repository code, documentation, evidence, logs, screenshots, exception text, command output, and Jira content may name an environment variable, but must never contain its value.

## Inventory

| Environment variable | Classification | Authorized purpose |
| --- | --- | --- |
| `CFBD_API_KEY` | Secret API credential | Read-only College Football Data retrieval after the applicable source-rights gate passes. |
| `GITHUB_TOKEN` | Secret control-plane credential | Authorized protected-repository operations with only the permissions required for the operation. |
| `JIRA_API_KEY` | Secret control-plane credential | Authorized project issue synchronization with only the permissions required for the operation. |
| `JIRA_EMAIL` | Sensitive identity binding | Bind `JIRA_API_KEY` to the Jira account; do not log or persist the configured identity value. |

`AGGIE_ANALYTICS_DATA_ROOT` is non-secret external path configuration, not a credential. Its value is still omitted from repository evidence because it can identify a user or host. The path contract is documented separately in `docs/operations/LOCAL_RUNTIME_PATHS.md`.

The machine-readable inventory is `artifacts/implementation_preflight/credential_inventory.redacted.json`. It records configured booleans and validation dispositions only. It contains no credential value, identity value, endpoint, response body, restricted payload, or absolute local path.

## Storage and process rules

- Supply values through the host environment, a secret manager that exports to the process environment, or an ignored local launcher file. The repository's `.env` path is ignored and must remain untracked.
- Reference a credential only by the environment-variable name above. Do not pass values on command lines, where process listings and shell history may retain them.
- Load values only in the process performing the authorized operation. Do not copy them into application configuration artifacts, forecast snapshots, provenance records, test fixtures, Jira, or GitHub content.
- Use the least privilege needed for the authorized operation. Authentication success does not establish that a token's scope or rotation policy is compliant; those properties require separate operator or provider evidence.
- Rotate or revoke a credential according to provider policy and immediately after suspected disclosure. No rotation interval or named secret owner is fabricated by this contract.
- A successful API authentication check does not grant source access, training, publication, redistribution, retention, or deletion rights. Source-rights decisions remain separate, explicit gates.

## Redaction before serialization

Operational metadata passes through `aggie_analytics.operations.observability.sanitize_metadata` before the JSONL event sink serializes it. Sensitive keys include authorization, cookie, password/passwd, secret, token, API-key variants, and credential. Bearer credentials and common credential-assignment patterns inside scalar text are replaced with `[REDACTED]`.

Redaction is a second safety boundary, not permission to log sensitive or restricted material. Callers must provide identifiers and metrics rather than raw responses, credential-bearing endpoints, provider payloads, headers, exception objects that may contain request material, or restricted URLs. Catch provider errors at the boundary and emit an allowlisted error class/status instead of raw response or exception text.

Representative synthetic tests cover nested sensitive keys, bearer and assignment strings, JSONL serialization, and an exception message. The completion evidence requires zero surviving synthetic markers. Real configured secret values are checked in memory against tracked files; only aggregate match counts may be persisted.

## Consumer gate

`POST-SUBTASK-006` must parse the machine-readable inventory and verify its schema, canonical content hash, prerequisite artifact identities, configured-name-only inventory, authentication dispositions, zero tracked-secret matches, redaction pass, and retained rights/release blockers. It must fail closed for missing or malformed input, hash or prerequisite drift, any included value or identity, an unconfigured required name, a failed smoke/redaction/leakage check, or missing provenance/rights state.

This contract proves only the non-repository credential inventory and redaction boundary. It does not claim source-rights approval, storage durability, historical-data materialization, production release readiness, a trained model, protected performance, AC-038, THR-011, or THR-012.
