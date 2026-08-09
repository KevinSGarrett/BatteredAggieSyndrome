# Source Credential Contract

Status: `IMPLEMENTED_CONTRACT_ONLY`  
Owner issue: `POST-SUBTASK-019` / `BAT-369`  
Production access readiness: `BLOCKED_PENDING_RIGHTS_AND_ACCESS_SMOKES`

## Boundary

This contract governs credentials used to retrieve external source data. Credential values remain outside Git, Jira, evidence, logs, screenshots, command lines, snapshots, and generated artifacts. The machine-readable companion is `artifacts/source_governance/credential_contract.redacted.json`; it contains names, roles, states, and hashes only.

Control-plane credentials (`GITHUB_TOKEN`, `JIRA_API_KEY`, and the `JIRA_EMAIL` identity binding) are governed by `docs/operations/CREDENTIALS_AND_SECRETS.md` and are not source credentials. `AGGIE_ANALYTICS_DATA_ROOT` is non-secret external path configuration.

This contract does not grant source rights, retention, training, publication, redistribution, or production approval. Authentication and rights are separate fail-closed gates.

## Defined source credential

| Environment variable | Provider/source binding | Purpose | Scope posture | Current contract state |
| --- | --- | --- | --- | --- |
| `CFBD_API_KEY` | CollegeFootballData, `SRC-002`; optional entitlement reuse for `SRC-059` only if separately approved | Read-only source retrieval | The provider credential is treated as unscoped because no scope-introspection evidence is claimed. Use only documented read operations and the minimum approved account tier. Mutation, administration, billing, sharing, and unrelated-provider use are prohibited. | Configured outside Git and previously authenticated read-only; still blocked from production use until source-rights and POST-SUBTASK-020/021 gates pass. |

No other source credential variable is defined by this task:

- Sources whose selected access mode requires no credential are bound to `NO_CREDENTIAL_REQUIRED`, not to a dummy secret.
- Open-Meteo free/no-key modes do not receive an invented key name. A customer-plan key may be named only after an approved plan, rights decision, and provider contract identify its actual interface.
- Optional market, commercial, licensed, portal, and proprietary lanes remain `CREDENTIAL_UNDEFINED_PENDING_LICENSE_AND_RIGHTS`. Their environment-variable names must be introduced by a controlled contract revision after legitimate access is obtained.
- Human or institutional portal logins are not converted into automation credentials. CAPTCHA, authentication, rate-limit, or access-control bypass is prohibited.

## Ownership and lifecycle

Named people are intentionally not fabricated. These accountable roles must be assigned in the operator's external access register before production activation:

| Role | Responsibility |
| --- | --- |
| `SOURCE_ACCESS_OWNER` | Approves provider account/tier, source-purpose binding, least-privilege posture, and continued operational need. |
| `SECRET_CUSTODIAN` | Creates, stores, rotates, revokes, and deletes the credential outside the repository. |
| `SECURITY_RESPONSE_OWNER` | Handles suspected exposure, coordinates revocation, and records incident closure. |
| `SOURCE_RIGHTS_REVIEWER` | Records the separate access, retention, training, publication, redistribution, and deletion decision. |

For `CFBD_API_KEY`, the external owner register must bind these roles before production use. Absence of a named role assignment is a production blocker, not permission to infer an owner.

Lifecycle rules:

1. Provision only after a provider account and authorized purpose exist. Never scrape, borrow, share, or repurpose another user's credential.
2. Store the value in a host secret manager, process environment, or ignored local launcher environment. The repository `.env` path is an allowed ignored local launcher input, never an artifact.
3. Review continued need and least-privilege posture at least every 90 days. This is a project review cadence, not a claim about provider expiry policy.
4. Rotate at the provider-required interval when one exists, and immediately after suspected disclosure, role change, unauthorized use, provider request, or scope/tier reduction.
5. Revoke before decommissioning an integration or removing an operator. Delete local copies after revocation and verify dependent jobs fail closed.
6. Record only redacted lifecycle metadata externally: variable name, provider alias, owner roles, created/rotated/revoked timestamps, provider terms/tier identity, and disposition. Never record the value or a reversible derivative.

## Expiry, revocation, and failure handling

- Missing, expired, revoked, malformed, or rejected credentials produce `BLOCKED_CREDENTIAL`; no anonymous downgrade is allowed for a lane whose contract requires authentication.
- Authentication failures must emit only an allowlisted provider alias, source ID, HTTP status class, and stable error code. Headers, URLs containing credentials, bodies, and raw exception text are prohibited.
- Retry behavior must respect provider policy and captured rate-limit metadata. Authentication failures are not retried as a rate-limit workaround.
- A successful response proves only that the credential worked for that request. It does not prove scope compliance, rights, schema stability, historical coverage, PIT safety, retention, redistribution, or production readiness.
- Revocation and deletion events invalidate cached readiness evidence. POST-SUBTASK-021 must return the affected source to `BLOCKED_CREDENTIAL` until fresh approved evidence exists.

## Consumer contract for POST-SUBTASK-020

POST-SUBTASK-020 must parse the redacted registry and verify its schema, content identity, prerequisite hashes, source bindings, storage boundary, owner-role requirements, lifecycle rules, and fail-closed states before any smoke request.

It must reject:

- a missing, stale, duplicate, unregistered, or cross-provider credential name;
- any credential value, identity value, authorization header, cookie, endpoint query secret, response body, or local absolute path in tracked or saved evidence;
- a required source binding whose configured state is false;
- an optional/licensed lane with no approved provider contract and source-rights decision;
- a claim that authentication implies access, retention, training, publication, redistribution, or production approval;
- an expired/revoked credential, missing owner-role assignment, or absent rotation/revocation/expiry behavior;
- a source contract that permits fallback around authentication, provider controls, or rate limits.

POST-SUBTASK-020 owns actual authenticated/no-key smoke execution and rate-limit/schema capture. POST-SUBTASK-021 owns final source-specific access readiness. Neither is completed by this document.

## Honesty boundary

The protected POST-SUBTASK-005 redacted inventory proves that the configured source credential remained outside Git and passed a prior read-only authentication smoke. This task does not persist or re-emit its value. Human source-rights review remains unresolved, no production source is approved, no bulk or historical source payload is materialized, and no empirical or release-readiness claim is made.
