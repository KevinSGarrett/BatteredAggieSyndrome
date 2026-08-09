# Source Credential Contract

Status: `IMPLEMENTED_CONTRACT_ONLY`  
Owner issue: `POST-SUBTASK-019` / `BAT-369`  
Production access readiness: `PRIVATE_RESEARCH_POLICY_ACTIVE_TECHNICAL_VALIDATION_PER_ROUTE`

## Boundary

This contract governs credentials used to retrieve external source data. Credential values remain outside Git, Jira, evidence, logs, screenshots, command lines, snapshots, and generated artifacts. The machine-readable companion is `artifacts/source_governance/credential_contract.redacted.json`; it contains names, roles, states, and hashes only.

Control-plane credentials (`GITHUB_TOKEN`, `JIRA_API_KEY`, and the `JIRA_EMAIL` identity binding) are governed by `docs/operations/CREDENTIALS_AND_SECRETS.md` and are not source credentials. `AGGIE_ANALYTICS_DATA_ROOT` is non-secret external path configuration.

This contract controls credential security and technical authentication only. The owner’s universal private-research policy separately allows acquisition, local retention, analysis, and model training for publicly accessible factual data and owner-credentialed routes. License, terms, redistribution, and upstream-authorization metadata are not authentication or private-use gates. Raw third-party publication remains outside this contract and requires a separate future review.

## Defined source credential

| Environment variable | Provider/source binding | Purpose | Scope posture | Current contract state |
| --- | --- | --- | --- | --- |
| `CFBD_API_KEY` | CollegeFootballData, `SRC-002`; any verified compatible endpoint binding | Read-only source retrieval | The provider credential is treated as unscoped because no scope-introspection evidence is claimed. Use only data-read operations needed by the project. Mutation, administration, billing, sharing, and unrelated-provider use are prohibited. | Configured outside Git and authenticated read-only; private acquisition is active, subject to quota and technical health. |
| `SCRAPFLY_API_TOKEN` | Scrapfly acquisition transport | Retrieve publicly accessible factual source pages | Read-only retrieval transport; never serialize the token or credential-bearing URL. | Configured outside Git; validate by redacted diagnostic before use. |
| `SCRAPFLY_MCP_URL` | Optional Scrapfly MCP transport | Route public-web acquisition through the configured integration | Treat embedded credential or signed components as secrets. | Configured outside Git; validate by redacted diagnostic before use. |
| `SCRAPERAPI_API_TOKEN` | ScraperAPI acquisition transport | Retrieve publicly accessible factual source pages | Read-only retrieval transport; never serialize the token or credential-bearing URL. | Configured outside Git; validate by redacted diagnostic before use. |

Other source credential variables are introduced only when their values actually exist and their provider binding is known:

- Sources whose selected access mode requires no credential are bound to `NO_CREDENTIAL_REQUIRED`, not to a dummy secret.
- Open-Meteo free/no-key modes do not receive an invented key name. A customer-plan key may be named only when configured and bound to its actual interface.
- Optional market, commercial, portal, and proprietary lanes without supplied credentials are `TECHNICAL_CREDENTIAL_NOT_CONFIGURED`; licensing status is non-blocking metadata.
- A genuinely private resource that requires credentials the owner has not supplied remains technically unavailable. Use a public equivalent route when one exists.

## Ownership and lifecycle

Named people are intentionally not fabricated. These accountable roles must be assigned in the operator's external access register before production activation:

| Role | Responsibility |
| --- | --- |
| `SOURCE_ACCESS_OWNER` | Approves provider account/tier, source-purpose binding, least-privilege posture, and continued operational need. |
| `SECRET_CUSTODIAN` | Creates, stores, rotates, revokes, and deletes the credential outside the repository. |
| `SECURITY_RESPONSE_OWNER` | Handles suspected exposure, coordinates revocation, and records incident closure. |

For configured credentials, the project owner is the authorization source. External role metadata improves operations but its absence does not recreate a source-acquisition approval gate.

Lifecycle rules:

1. Provision only for this project with the owner’s authorization. Never borrow, share, expose, or repurpose another user's credential.
2. Store the value in a host secret manager, process environment, or ignored local launcher environment. The repository `.env` path is an allowed ignored local launcher input, never an artifact.
3. Review continued need and least-privilege posture at least every 90 days. This is a project review cadence, not a claim about provider expiry policy.
4. Rotate at the provider-required interval when one exists, and immediately after suspected disclosure, role change, unauthorized use, provider request, or scope/tier reduction.
5. Revoke before decommissioning an integration or removing an operator. Delete local copies after revocation and verify dependent jobs fail closed.
6. Record only redacted lifecycle metadata externally: variable name, provider alias, owner roles, created/rotated/revoked timestamps, provider terms/tier identity, and disposition. Never record the value or a reversible derivative.

## Expiry, revocation, and failure handling

- Missing, expired, revoked, malformed, or rejected credentials produce `TECHNICAL_CREDENTIAL_UNAVAILABLE` for that route. Autonomously use an equivalent public or configured route when available; do not mislabel the condition as a rights block.
- Authentication failures must emit only an allowlisted provider alias, source ID, HTTP status class, and stable error code. Headers, URLs containing credentials, bodies, and raw exception text are prohibited.
- Retry behavior must use bounded backoff and captured rate-limit metadata. Authentication failures are not retried as a rate-limit workaround.
- A successful response proves only that the credential worked for that request. It does not prove schema stability, historical coverage, data quality, PIT safety, or production readiness.
- Revocation and deletion events invalidate cached technical-readiness evidence. The affected route returns to `TECHNICAL_CREDENTIAL_UNAVAILABLE` until fresh evidence exists; equivalent routes remain independently usable.

## Consumer contract for POST-SUBTASK-020

POST-SUBTASK-020 must parse the redacted registry and verify its schema, content identity, prerequisite hashes, source bindings, storage boundary, owner-role requirements, lifecycle rules, and fail-closed states before any smoke request.

It must reject:

- a missing, stale, duplicate, unregistered, or cross-provider credential name;
- any credential value, identity value, authorization header, cookie, endpoint query secret, response body, or local absolute path in tracked or saved evidence;
- a required source binding whose configured state is false;
- a genuinely private lane requiring a credential that has not been supplied;
- a claim that authentication implies schema compatibility, historical coverage, data quality, PIT safety, or production readiness;
- an expired/revoked credential, missing owner-role assignment, or absent rotation/revocation/expiry behavior;
- a source contract that exposes credentials or treats a failed authenticated request as successful evidence.

POST-SUBTASK-020 owns actual authenticated/no-key smoke execution and rate-limit/schema capture. POST-SUBTASK-021 owns final source-specific access readiness. Neither is completed by this document.

## Honesty boundary

The protected POST-SUBTASK-005 redacted inventory proves that configured source credentials remained outside Git and that CFBD passed a prior read-only authentication smoke. This task does not persist or re-emit credential values. The universal private-research policy supersedes the former human source-rights prerequisite. Technical readiness, schema compatibility, historical coverage, PIT safety, quality, and downstream empirical readiness remain separately evidenced; this document alone makes no empirical or release-readiness claim.
